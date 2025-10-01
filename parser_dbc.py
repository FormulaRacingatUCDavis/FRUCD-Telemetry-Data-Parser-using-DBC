import cantools
from pprint import pprint
import csv
import os
import sys
import math

if len(sys.argv) < 2:
    print("Provide a file type flag: -s for SavvyCAN, -r for Raspberry Pi")
    exit()
    
flag = sys.argv[1]

if not (flag == '-r' or flag == '-s'):
    print("Provide a file type flag: -s for SavvyCAN, -r for Raspberry Pi")
    exit()

# load CAN database info
db = cantools.database.load_file('./FE12.dbc')
db2 = cantools.database.load_file('./20240625 Gen5 CAN DB.dbc')

class CAN_Message:
    # initialize with raw string slices from csv row
    def __init__(self, timestamp: str, arbitration_id: str , data: list[str]):
        self.timestamp:int = int(timestamp) if flag == '-s' else int(timestamp, 16)
        self.arbitration_id:int = int(arbitration_id, 16)
        self.data:bytes = bytes((int(n,16) if n else 0) for n in data)

    def get_decoded_message_as_list(self):
        decoded_msg = db.decode_message(self.arbitration_id, self.data)
        
        result_list = [self.timestamp]

        # ===== for raw ADC current ======
        # (delete later)
        current_raw = 0
        # ================================
        for signal_name, value in decoded_msg.items():

            # ==== special case for raw ADC data ===== 
            # (too lazy to make this cleaner, delete this section after changing PEI code to send converted data)
            
            if (self.arbitration_id == 0x382 and signal_name == "HI_Temp_ADC_Reading" ) or \
               (self.arbitration_id == 0x384 and (signal_name == "Temp_1_ADC_Reading" or \
                                                  signal_name == "Temp_2_ADC_Reading" or \
                                                  signal_name == "Temp_3_ADC_Reading")):
                # temps
                temp_voltage = (value * 0.00015) + 1.5
                # print(id, signal_name, value)
                try:
                    temp = (1.0 / ((1.0 / 298.15) + ((1.0 / 3934.0) * math.log(temp_voltage / (3 - temp_voltage))))) - 273.15
                    result_list.append(temp)
                except:
                    print(f"invalid value: {value}, id: {self.arbitration_id}, signal: {signal_name}")
            elif self.arbitration_id == 0x388:
                if signal_name == "Current_ADC_Reading": 
                    # current
                    current_raw = value # only save the value. append to list after actual current is calculated w/ current ref
                if signal_name == "Current_Reference_ADC_Reading":
                    # current ref
                    mvolts = (current_raw / 4095) * 3.3 * 1000
                    mvolt_ref = (value / 4095) * 3.3 * 1000
                    current = ((mvolts - mvolt_ref) * 7.4 / 4.7) / 6.667
                    result_list.append(current)
            elif (self.arbitration_id == 0x382 and signal_name == "Pack_Voltage") or \
                 (self.arbitration_id == 0x383 and (signal_name == "Voltage_1_ADC_Reading" or \
                                                    signal_name == "Voltage_2_ADC_Reading" or \
                                                    signal_name == "Voltage_3_ADC_Reading")): 
                # voltages
                voltage = (value * 0.00015) + 1.5
                result_list.append(voltage)
            else:
            # ========================================
                result_list.append(value)
        
        return result_list
            


input_files_directory = "../"  # all data files are expected to be in ../

output_directory = "../parsed"

os.makedirs(output_directory, exist_ok=True) # make output directory in filesystem

# clear output directory
for filename in os.listdir(output_directory):
    file_path = os.path.join(output_directory, filename)
    if os.path.isfile(file_path):  # only delete files
        os.remove(file_path)

# for every file in input directory
for filename in os.listdir(input_files_directory):
    input_file_path = os.path.join(input_files_directory, filename)
    if os.path.isfile(input_file_path):  # check if is a file, not a subdirectory

        can_messages = {} # all messages in CAN_Message format, hashed to their message id
        temp_CAN_message = None

        # read file and store messages in can_messages
        with open(input_file_path, newline='') as csvfile:
            csv_contents = csv.reader(csvfile, delimiter=',', quotechar='|')
            isFirstRow = True

            # for savvycan timestamps
            cum_time = 0
            prev_raw_timestamp = 0

            for row in csv_contents:
                if isFirstRow:
                    isFirstRow = False
                    continue

                if flag == '-s':
                    # fix savvycan timestamps, which overflow at 1000000ms and wrap back to 0 =========
                    raw_timestamp = int(row[0])
                    time_diff = raw_timestamp - prev_raw_timestamp 
                    if time_diff >= 0: 
                        cum_time += time_diff
                    else: # time wrapped to 0
                        cum_time += ((1000000 - prev_raw_timestamp) + raw_timestamp)
                    # =================================================================================

                    temp_CAN_message = CAN_Message(str(cum_time), row[1], row[6:])
                else:
                    temp_CAN_message = CAN_Message(row[9], row[0], row[1:9])
                
                if not temp_CAN_message.arbitration_id in can_messages:
                    can_messages[temp_CAN_message.arbitration_id] = []
                can_messages[temp_CAN_message.arbitration_id].append(temp_CAN_message)

        for id in can_messages:
            # look up message info in db
            db_message_info = db.get_message_by_frame_id(id)

            # creat output file path
            name, ext = os.path.splitext(filename)
            out_file_path = output_directory + "/" + name + "_parsed_" + db_message_info.name + ".csv"

            # init new decoded file
            with open(out_file_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)

                # write header row
                header_row_list = ["timestamp (ms)"]
                for signal in db_message_info.signals: # write every signal name and unit

                    # ==== special case for raw ADC data ===== 
                    # (too lazy to make this cleaner, delete this section after changing PEI code to send converted data)
                    
                    if (id == 0x382 and signal.name == "HI_Temp_ADC_Reading" ) or \
                       (id == 0x384 and (signal.name == "Temp_1_ADC_Reading" or \
                                         signal.name == "Temp_2_ADC_Reading" or \
                                         signal.name == "Temp_3_ADC_Reading")):
                        # temps
                        header_row_list.append(signal.name + " (C)")
                    elif id == 0x388: 
                        # current
                        header_row_list.append("PEI_Current (A)")
                        break
                    elif (id == 0x382 and signal.name == "Pack_Voltage") or \
                         (id == 0x383 and (signal.name == "Voltage_1_ADC_Reading" or \
                                           signal.name == "Voltage_2_ADC_Reading" or \
                                           signal.name == "Voltage_3_ADC_Reading")): 
                        # voltages
                        header_row_list.append(signal.name + " (V)")
                    else:
                    # ========================================
                        header_row_list.append(signal.name + f" ({signal.unit})")
                writer.writerow(header_row_list) 

                # write all data rows for current message id
                for message in can_messages[id]:
                    writer.writerow(message.get_decoded_message_as_list())
                
                

