# FRUCD Telemetry Data Parser using DBC
This application converts raw telem data files to CSV files with human-readable units and labels.

To use, make sure this DBC parser folder is inside the folder with all the raw telem data files! Folder structure should be as such:  
```
some_track_day_data_folder /  
    parser_dbc /
        ...
        parser_dbc.py
    data1.csv
    data2.csv
    data3.csv
    ...
```

Steps:  
1. Have python installed  
2. Navigate to this parser_dbc folder in the terminal  
3. Type the following  
```
python parser_dbc.py [input_format_flag] [combine_files_flag]
```
Replace `[input_format_flag]` with flag for the appropriate input file format:  
- -s : SavvyCAN  
- -r : Raspberry Pi    

Replace `[combine_files_flag]` with:  
- -c : to combine all files in order of creation date (in the metadata)  
- nothing, if you don't want to combine them 

For example:  
```
python parser_dbc.py -s
```
to parse all SavvyCAN files in the folder.   

**Note: as of the first version, only -s is supported.**


