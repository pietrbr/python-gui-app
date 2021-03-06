#!/usr/bin/env python3

import PySimpleGUI as sg
from csv import DictWriter
from Sensors.Camera import MLX90614_GY906
from Sensors.LightSensor import TSL2591
from Sensors.Pressure import BME280
from Sensors.Temperature import DHT22
from Sensors.UVSensor import LTR390
from Sensors.GPS import GPS

from random import random
import logging

from FileManager.Openfile import WindowOpenFile

logging.basicConfig(level=logging.INFO,
                    filename='app_logs.log',
                    filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')


def make_window(theme):
    sg.theme(theme)
    menu_def = [['&Application', ['&Create and open file']],
                ['&Help', ['&About']]]

    app_layout = [
        [
            sg.Text('Location:', size=(10, 1)),
            sg.Input(size=(15, 1), key='-LOCATION-'),
            # sg.Text('', size=(12, 1)),
            sg.Button('Acquire all', size=(18, 1)),
            sg.Button('Save', size=(10, 1))
        ],
        [
            sg.Text('Wind speed:', size=(10, 1)),
            sg.Input(size=(15, 1), key='-WIND_SPEED-'),
            sg.Text("m/s"),
            sg.Text('Ground humidity:', size=(15, 1)),
            sg.Input(size=(10, 1), key='-GROUND_HUM-'),
            sg.Text("%")
        ],
        [
            sg.Button('Air temperature', size=(20, 1)),
            sg.ProgressBar(100,
                           orientation='h',
                           size=(10, 20),
                           key='-PROGRESS BAR AIR-'),
            sg.Text(size=(5, 1), key='-AIR DISPLAY-'),
            sg.Text("°C")
        ],
        [
            sg.Button('Canopy temperature', size=(20, 1)),
            sg.ProgressBar(100,
                           orientation='h',
                           size=(10, 20),
                           key='-PROGRESS BAR CANOPY-'),
            sg.Text(size=(5, 1), key='-CANOPY DISPLAY-'),
            sg.Text("°C")
        ],
        [
            sg.Button('Humidity', size=(20, 1)),
            sg.ProgressBar(100,
                           orientation='h',
                           size=(10, 20),
                           key='-PROGRESS BAR HUMIDITY-'),
            sg.Text(size=(5, 1), key='-HUMIDITY DISPLAY-'),
            sg.Text("%")
        ],
        [
            sg.Button('Pressure', size=(20, 1)),
            sg.ProgressBar(100,
                           orientation='h',
                           size=(10, 20),
                           key='-PROGRESS BAR PRESSURE-'),
            sg.Text(size=(5, 1), key='-PRESSURE DISPLAY-'),
            sg.Text("hPa")
        ],
        [
            sg.Button('IR radiation', size=(20, 1)),
            sg.ProgressBar(100,
                           orientation='h',
                           size=(10, 20),
                           key='-PROGRESS BAR RADIATION-'),
            sg.Text(size=(5, 1), key='-IR RADIATION DISPLAY-'),
            sg.Text("W/m\u00b2")
        ],
        [
            sg.Button('UV radiation', size=(20, 1)),
            sg.ProgressBar(100,
                           orientation='h',
                           size=(10, 20),
                           key='-PROGRESS BAR UV RADIATION-'),
            sg.Text(size=(5, 1), key='-UV RADIATION DISPLAY-'),
            sg.Text("W/m\u00b2")
        ]
    ]

    logging_layout = [[sg.Text("Anything printed will display here!")],
                      [
                          sg.Multiline(size=(60, 15),
                                       font='Courier 8',
                                       expand_x=True,
                                       expand_y=True,
                                       write_only=True,
                                       reroute_stdout=True,
                                       reroute_stderr=True,
                                       echo_stdout_stderr=True,
                                       autoscroll=True,
                                       auto_refresh=True)
                      ]]

    theme_layout = [[
        sg.Text(
            "See how elements look under different themes by choosing a different theme here!"
        )
    ],
                    [
                        sg.Listbox(values=sg.theme_list(),
                                   size=(20, 12),
                                   key='-THEME LISTBOX-',
                                   enable_events=True)
                    ], [sg.Button("Set Theme")]]

    layout = [[
        sg.MenubarCustom(menu_def,
                         key='-MENU-',
                         font='Courier 15',
                         tearoff=False)
    ]]
    layout += [[
        sg.TabGroup([[
            sg.Tab('Measures', app_layout),
            sg.Tab('Logs', logging_layout),
            sg.Tab('Themes', theme_layout)
        ]],
                    key='-TAB GROUP-',
                    expand_x=True,
                    expand_y=True),
    ]]
    layout[-1].append(sg.Sizegrip())
    window = sg.Window(
        'Data collection application',
        layout,
        grab_anywhere=False,
        resizable=True,
        margins=(0, 0),
        # use_custom_titlebar=True,
        finalize=True,
        keep_on_top=True,
        scaling=1.0)
    window.set_min_size(window.size)
    return window


def main():
    window = make_window(sg.theme())
    logging.info('New window opened')
    fpath = None
    # headers for csv file
    headersCSV = [
        'CODE', 'LAT', 'LON', 'AIR_TEMP', 'CANOPY_TEMP', 'HUM', 'GROUND_HUM',
        'WIND_SPEED', 'PRESSURE', 'IR_RAD', 'UV_RAD'
    ]
    # keys of dictonary for displayed values
    display_dict = [
        # '-LAT DISPLAY-', '-LON DISPLAY-',
        '-AIR DISPLAY-',
        '-CANOPY DISPLAY-',
        '-HUMIDITY DISPLAY-',
        '-PRESSURE DISPLAY-',
        '-IR RADIATION DISPLAY-',
        '-UV RADIATION DISPLAY-'
    ]
    # keys of dictonary for displayed bars
    bar_dict = [
        '-PROGRESS BAR AIR-', '-PROGRESS BAR CANOPY-',
        '-PROGRESS BAR HUMIDITY-', '-PROGRESS BAR PRESSURE-',
        '-PROGRESS BAR RADIATION-', '-PROGRESS BAR UV RADIATION-'
    ]
    # dictonary for values acquired
    # reset dictonary values to 'None' to get ready for next collection
    dict = {
        'CODE': None,
        'LAT': None,
        'LON': None,
        'AIR_TEMP': None,
        'CANOPY_TEMP': None,
        'HUM': None,
        'GROUND_HUM': None,
        'WIND_SPEED': None,
        'PRESSURE': None,
        'IR_RAD': None,
        'UV_RAD': None
    }
    value = None
    window['-LOCATION-'].update('')  # CODE
    for key in display_dict:  # -DISPLAY-
        window[key].update('-')
    for key in bar_dict:  # -PROGRESS BAR-
        window[key].update(0)

    # ---------------------------------------------------
    # Initialize Each Sensor
    # ---------------------------------------------------
    tempSensor = DHT22('Sensore di Temperatura e Umidità')
    lightSensor = TSL2591('Sensore di Luce Ambientale')
    uvSensor = LTR390('Sensore Radiazione Ultravioletta')
    cameraIR = MLX90614_GY906('Sensore di Temperatura Superficiale')
    pressSensor = BME280('Sensore di Pressione, Temperatura e umidità')
    gps = GPS(name='Sensore Coordinate GPS', port="/dev/ttyAMA0")
    logging.info('Sensors calibrated')

    pressSensor.get_calib_param()
    logging.info('Got calib params of pressure sensor')
    # ---------------------------------------------------

    while True:  # This is the Event Loop
        event, values = window.read(timeout=100)
        if event not in (sg.TIMEOUT_EVENT, sg.WIN_CLOSED):
            print('=======================================\n', 'EVENT = ',
                  event)
            le = 0
            for key in values:
                if len(key) > le:
                    le = len(key)
            for key in values:
                print(' ' * 6, key, ' ' * (le - len(key)), '= ', values[key])
        if event in (None, 'Exit'):
            print("EVENT = Clicked Exit!")
            break

        ### SENSOR ACQUISITION ###
        elif event == 'Air temperature':
            temp1, _ = tempSensor.measure()
            temp2 = pressSensor.measure()
            # temp1 = 12
            # temp2 = (13, 14)
            value = (
                temp1 + temp2[1]
            ) / 2  # Take the average between the two temp by diff sensors
            window['-AIR DISPLAY-'].update("{:.2f}".format(
                value))  # TODO: change here for acquisition # DONE
            progress_bar = window['-PROGRESS BAR AIR-']
            [progress_bar.update(current_count=i + 1) for i in range(100)]
            dict['AIR_TEMP'] = round(value, 2)
            value = None
            logging.info("Air temperature measurement complete")

        elif event == 'Canopy temperature':
            value = cameraIR.measure()  # TODO: change here for acquisition
            window['-CANOPY DISPLAY-'].update("{:.2f}".format(value))
            progress_bar = window['-PROGRESS BAR CANOPY-']
            [progress_bar.update(current_count=i + 1) for i in range(100)]
            dict['CANOPY_TEMP'] = round(value, 2)
            value = None
            logging.info("Canopy temperature measurement complete")

        elif event == 'Humidity':
            _, value = tempSensor.measure()
            temp = pressSensor.measure()
            value = (value + temp[1]) / 2
            window['-HUMIDITY DISPLAY-'].update("{:.2f}".format(
                value))  # TODO: change here for acquisition # DONE
            progress_bar = window['-PROGRESS BAR HUMIDITY-']
            [progress_bar.update(current_count=i + 1) for i in range(100)]
            dict['HUM'] = round(value, 2)
            value = None
            logging.info("Humidity measurement complete")

        elif event == 'Pressure':
            value = pressSensor.measure()
            value = value[0]
            window['-PRESSURE DISPLAY-'].update("{:.2f}".format(value))
            progress_bar = window['-PROGRESS BAR PRESSURE-']
            [progress_bar.update(current_count=i + 1) for i in range(100)]
            dict['PRESSURE'] = round(value, 2)
            value = None
            logging.info("Pressure measurement complete")

        elif event == 'IR radiation':
            value = lightSensor.measure()
            # value = 12
            window['-IR RADIATION DISPLAY-'].update("{:.2f}".format(value))
            progress_bar = window['-PROGRESS BAR RADIATION-']
            [progress_bar.update(current_count=i + 1) for i in range(100)]
            dict['IR_RAD'] = round(value, 2)
            value = None
            logging.info("IR radiation measurement complete")

        elif event == 'UV radiation':
            value = uvSensor.measure()
            # value = 12
            window['-UV RADIATION DISPLAY-'].update("{:.2f}".format(value))
            progress_bar = window['-PROGRESS BAR UV RADIATION-']
            [progress_bar.update(current_count=i + 1) for i in range(100)]
            dict['UV_RAD'] = round(value, 2)
            value = None
            logging.info("UV radiation measurement complete")

        elif event == 'Acquire all':
            # AIR TEMPERATURE
            temp1, _ = tempSensor.measure()
            temp2 = pressSensor.measure()
            # temp1 = 12
            # temp2 = 13
            value = (
                temp1 + temp2[1]
            ) / 2  # Take the average between the two temp by diff sensors
            window['-AIR DISPLAY-'].update("{:.2f}".format(
                value))  # TODO: change here for acquisition # DONE
            progress_bar = window['-PROGRESS BAR AIR-']
            [progress_bar.update(current_count=i + 1) for i in range(100)]
            dict['AIR_TEMP'] = round(value, 2)
            value = None
            logging.info("Air temperature measurement complete")

            # CANOPY TEMPERATURE
            value = cameraIR.measure()
            window['-CANOPY DISPLAY-'].update("{:.2f}".format(value))
            progress_bar = window['-PROGRESS BAR CANOPY-']
            [progress_bar.update(current_count=i + 1) for i in range(100)]
            dict['CANOPY_TEMP'] = round(value, 2)
            value = None
            logging.info("Canopy temperature measurement complete")

            # HUMIDITY
            _, value = tempSensor.measure()
            temp = pressSensor.measure()
            value = (value + temp[1]) / 2
            window['-HUMIDITY DISPLAY-'].update("{:.2f}".format(
                value))  # TODO: change here for acquisition # DONE
            progress_bar = window['-PROGRESS BAR HUMIDITY-']
            [progress_bar.update(current_count=i + 1) for i in range(100)]
            dict['HUM'] = round(value, 2)
            value = None
            logging.info("Humidity measurement complete")

            # PRESSURE
            value = pressSensor.measure()
            value = value[0]
            window['-PRESSURE DISPLAY-'].update("{:.2f}".format(value))
            progress_bar = window['-PROGRESS BAR PRESSURE-']
            [progress_bar.update(current_count=i + 1) for i in range(100)]
            dict['PRESSURE'] = round(value, 2)
            value = None
            logging.info("Pressure measurement complete")

            # INFRARED
            value = lightSensor.measure()
            window['-IR RADIATION DISPLAY-'].update("{:.2f}".format(value))
            progress_bar = window['-PROGRESS BAR RADIATION-']
            [progress_bar.update(current_count=i + 1) for i in range(100)]
            dict['IR_RAD'] = round(value, 2)
            value = None
            logging.info("IR radiation measurement complete")

            # ULTRAVIOLET
            value = uvSensor.measure()
            window['-UV RADIATION DISPLAY-'].update("{:.2f}".format(value))
            progress_bar = window['-PROGRESS BAR UV RADIATION-']
            [progress_bar.update(current_count=i + 1) for i in range(100)]
            dict['UV_RAD'] = round(value, 2)
            value = None
            logging.info("UV radiation measurement complete")

        # END OF ACQUIRE ALL

        elif event == "Set Theme":
            logging.info("Clicked Set Theme")
            theme_chosen = values['-THEME LISTBOX-'][0]
            logging.info("User Chose Theme: " + str(theme_chosen))
            window.close()
            window = make_window(theme_chosen)

        ### CREATE AND OPEN FILE ###
        elif event == 'Create and open file':
            logging.info('Clicked Create and open file')
            window_open_file = WindowOpenFile(headersCSV, theme=sg.theme())
            fpath = window_open_file.getfilename(
            )[:]  # attach [:] to make a copy of the string
            logging.info('File created and saved - path: ', fpath)
            del window_open_file

        ### SAVE DATA TO FILE ###
        # check here on how to write csv files: https://www.delftstack.com/howto/python/python-append-to-csv/
        elif event == 'Save':
            logging.info('Clicked Save')
            with open(fpath, 'a', newline='') as f:
                dict['CODE'] = values['-LOCATION-']
                dict['WIND_SPEED'] = values['-WIND_SPEED-']
                dict['GROUND_HUM'] = values['-GROUND_HUM-']
                # Acquire Data from GPS
                lat, lng = gps.measure()
                # lat, lng = random(), random()
                # dict['LAT'] = round(lat, 2)
                # dict['LON'] = round(lng, 2)
                dictwriter = DictWriter(f, fieldnames=headersCSV)
                dictwriter.writerow(dict)
                f.close()
            # reset dict entries and values to 'None' to get ready for next collection
            dict = {
                'CODE': None,
                'LAT': None,
                'LON': None,
                'AIR_TEMP': None,
                'CANOPY_TEMP': None,
                'HUM': None,
                'GROUND_HUM': None,
                'WIND_SPEED': None,
                'PRESSURE': None,
                'IR_RAD': None,
                'UV_RAD': None
            }
            value = None
            for key in display_dict:
                window[key].update('-')
            for key in bar_dict:
                window[key].update(0)
            for key in ['-LOCATION-', '-WIND_SPEED-', '-GROUND_HUM-']:
                window[key].update('')

        elif event == 'About':
            logging.info("Clicked About")
            sg.popup(
                'Application for the collection of data for the ANSIA Team of the ASP Program XVII cycle.',
                'The application was kindly designed by the online boys.',
                'The application is based on the design provided in the PySimpleGUI Demo All Elements.',
                '',
                # 'The app may contain an easter egg...or not',
                '',
                keep_on_top=True)

    window.close()
    exit(0)


if __name__ == '__main__':
    sg.theme('Python')
    main()
