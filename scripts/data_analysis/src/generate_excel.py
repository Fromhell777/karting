import numpy as np

import copy
import argparse
import yaml
import xlsxwriter

#################
# Input parsing #
#################
parser = argparse.ArgumentParser(description = "Analyse the karting data and " +
                                               "generate an Excel file.")

parser.add_argument("-i", "--input",
                    required = True,
                    help     = "The input YAML file containing all the karting data")
parser.add_argument("-o", "--output",
                    required = True,
                    help     = "The output Excel file containing the analysed " +
                               "karting data")

args = parser.parse_args()

################
# data parsing #
################
with open(args.input, 'r') as data_file:
  karting_data = yaml.safe_load(data_file)

##########################
# Precalculate some data #
##########################
number_of_teams = len(karting_data["results"])

total_race_time = 0
for lap in karting_data["results"][0]["laps"]:
  total_race_time += lap["time"]

cumulative_times = {}
for team_data in karting_data["results"]:
  times = [lap["time"] for lap in team_data["laps"]]
  cumulative_times[team_data["team_name"]] = np.cumsum(times)

running_averages = {}
for team_data in karting_data["results"]:
  team_name = team_data["team_name"]
  cumulative_time = cumulative_times[team_name]
  running_averages[team_name] = cumulative_time / np.arange(1, len(cumulative_time) + 1)

# Update the cumulative times for easier interpolation
cumulative_times_extended = copy.deepcopy(cumulative_times)
for team_name in cumulative_times_extended:
  # Add the value 0 to start of the cumulative times
  cumulative_times_extended[team_name] = np.insert(cumulative_times_extended[team_name], 0, 0)

max_cumulative_time = max([cumulative_time[-1] for cumulative_time in cumulative_times.values()])
for team_name in cumulative_times_extended:
  # Extend the cumulative times with the last running average of the team
  while cumulative_times_extended[team_name][-1] < max_cumulative_time:
    cumulative_times_extended[team_name] = np.append(cumulative_times_extended[team_name],
                                                     cumulative_times_extended[team_name][-1] + running_averages[team_name][-1])

# Calculate interpolated laps
all_cumulative_times = []
for team_cumulative_times in cumulative_times.values():
  all_cumulative_times.extend(team_cumulative_times)

all_cumulative_times.sort()

# Here we assume that no team stopped or got disqualified
interpolated_laps = {}
for team_name, team_cumulative_times_extended in cumulative_times_extended.items():
  interpolated_laps[team_name] = []
  current_lap_index = 0
  for cumulative_time in all_cumulative_times:
    while team_cumulative_times_extended[current_lap_index + 1] < cumulative_time:
      current_lap_index += 1

    # Interpolate
    current_cumulative_time = team_cumulative_times_extended[current_lap_index]
    next_cumulative_time    = team_cumulative_times_extended[current_lap_index + 1]
    interpolated_lap = current_lap_index + (cumulative_time - current_cumulative_time) / \
                                           (next_cumulative_time - current_cumulative_time)
    interpolated_laps[team_name].append(interpolated_lap)

total_running_average = []
for i, cumulative_time in enumerate(all_cumulative_times):
  sum_team_laps = sum([team_interpolated_laps[i] for team_interpolated_laps in interpolated_laps.values()])
  total_running_average.append(number_of_teams * cumulative_time / sum_team_laps)

total_running_average_diff = {}
for team_name in cumulative_times:
  total_running_average_diff[team_name] = []
  for i, cumulative_time in enumerate(all_cumulative_times):
    total_running_average_diff[team_name].append(cumulative_time / interpolated_laps[team_name][i] -
                                                 total_running_average[i])

###############
# Excel setup #
###############
# Create a workbook and add a worksheet
workbook = xlsxwriter.Workbook(filename = args.output,
                               options  = {"use_future_functions" : True})
worksheet_results      = workbook.add_worksheet("results")
worksheet_race_data    = workbook.add_worksheet("race_data")
worksheet_intermediate = workbook.add_worksheet("intermediate_data")

# Create the cell formats
header_format = workbook.add_format()
header_format.set_bold()
header_format.set_font_color("#44546A")
header_format.set_font_size(13)
header_format.set_align("center")

cell_format = workbook.add_format()
cell_format.set_align("right")

merge_format = workbook.add_format()
merge_format.set_align("center")

# Set the column width
worksheet_results.set_column(first_col = 0,
                             last_col  = 11,
                             width     = 30)

worksheet_race_data.set_column(first_col = 0,
                               last_col  = number_of_teams * 5 - 2,
                               width     = 30)

worksheet_intermediate.set_column(first_col = 0,
                                  last_col  = number_of_teams * 4 + 1,
                                  width     = 40)

# Sort the input data on position for consistency
karting_data["results"].sort(key = lambda team_data: team_data["finish_position"])

####################
# Helper functions #
####################
def count_drivers(karting_data):
  drivers = set()
  for team_data in karting_data["results"]:
    for lap in team_data["laps"]:
      if lap["driver"] != "Pit":
        drivers.add(lap["driver"])

  return len(drivers)

def create_table(worksheet,
                 table_options,
                 first_row,
                 last_row,
                 first_column,
                 last_column,
                 header_format,
                 cell_format):

  for column in table_options["columns"]:
    column["format"] = cell_format

  table_options["style"] = None

  worksheet.add_table(first_row = first_row,
                      first_col = first_column,
                      last_row  = last_row,
                      last_col  = last_column,
                      options   = table_options)

  headers = [column["header"] for column in table_options["columns"]]
  for i, header in enumerate(headers):
    worksheet.write_string(row         = first_row,
                           col         = first_column + i,
                           string      = header,
                           cell_format = header_format)

def calc_next_multiple(number, multiple):
  return ((number + multiple) // multiple) * multiple

def calc_previous_multiple(number, multiple):
  return (number // multiple) * multiple

def get_race_time_axis_units(total_race_time):
  if total_race_time > 5000:
    major_unit = 1000
  elif total_race_time > 2500:
    major_unit = 500
  elif total_race_time > 1000:
    major_unit = 250
  else:
    major_unit = 100

  minor_unit = major_unit / 5

  return (major_unit, minor_unit)

def get_laps_axis_units(lap_range):
  if lap_range > 5:
    major_unit = 0.5
  elif lap_range > 2.5:
    major_unit = 0.25
  elif lap_range > 1:
    major_unit = 0.125
  else:
    major_unit = 0.1

  minor_unit = major_unit / 5

  return (major_unit, minor_unit)

def set_default_axis_options(chart,
                             x_name,
                             x_min,
                             x_max,
                             x_major_unit,
                             x_minor_unit,
                             y_name,
                             y_min,
                             y_max,
                             y_major_unit,
                             y_minor_unit):
  chart.set_x_axis({"name"            : x_name,
                    "min"             : x_min,
                    "max"             : x_max,
                    "major_gridlines" : {"visible" : True},
                    "minor_gridlines" : {"visible" : True},
                    "major_unit"      : x_major_unit,
                    "minor_unit"      : x_minor_unit,
                    "label_position"  : "low"})
  chart.set_y_axis({"name"            : y_name,
                    "min"             : y_min,
                    "max"             : y_max,
                    "major_gridlines" : {"visible" : True},
                    "minor_gridlines" : {"visible" : True},
                    "major_unit"      : y_major_unit,
                    "minor_unit"      : y_minor_unit,
                    "label_position"  : "low"})

######################
# Total team results #
######################
total_data = []
for team_data in karting_data["results"]:
  total_data.append([team_data["finish_position"],
                     team_data["kart_number"],
                     team_data["team_name"],
                     None,
                     team_data["distance_to_winner"]])

team_table_name = "\"team\" & race_results[[#This Row], [Position]] & \"_results"

table_options = {"name"    : "race_results",
                 "data"    : total_data,
                 "columns" : [{"header"  : "Position"},
                              {"header"  : "Kart number"},
                              {"header"  : "Team"},
                              {"header"  : "Laps [laps]",
                               "formula" : f"=COUNT(INDIRECT({team_table_name}[Lap times '[sec']]\"))"},
                              {"header"  : "Distance"},
                              {"header"  : "Fastest lap [laps]",
                               "formula" : f"=MIN(INDIRECT({team_table_name}[Lap times '[sec']]\"))"},
                              {"header"  : "Slowest lap [laps]"},
                              {"header"  : "Average lap [sec]",
                               "formula" : f"=SUM(INDIRECT({team_table_name}[Lap times '[sec']]\")) / race_results[[#This Row], [Laps '[laps']]]"},
                              {"header"  : "Standard deviation [sec]"},
                              {"header"  : "Pit time [sec]",
                               "formula" : f"=SUMIF(INDIRECT({team_table_name}[Driver]\"), \"Pit\", INDIRECT({team_table_name}[Lap times '[sec']]\"))"},
                              {"header"  : "Pit stops",
                               "formula" : f"=COUNTIF(INDIRECT({team_table_name}[Driver]\"), \"Pit\")"},
                              {"header"  : "Average pit time [sec]",
                               "formula" : "=race_results[[#This Row], [Pit time '[sec']]] / race_results[[#This Row], [Pit stops]]"}]}

# Slowest lap formula
for i in range(len(total_data)):
  worksheet_results.write_formula(row     = i + 2,
                                  col     = 6,
                                  formula = f"{{=MAX(IF(INDIRECT({team_table_name}[Driver]\") <> \"Pit\", INDIRECT({team_table_name}[Lap times '[sec']]\")))}}")

# Standard deviation formula
for i in range(len(total_data)):
  worksheet_results.write_formula(row     = i + 2,
                                  col     = 8,
                                  formula = f"{{=STDEV.S(IF(INDIRECT({team_table_name}[Driver]\") <> \"Pit\", INDIRECT({team_table_name}[Lap times '[sec']]\")))}}")

create_table(worksheet     = worksheet_results,
             table_options = table_options,
             first_row     = 1,
             last_row      = 1 + len(total_data),
             first_column  = 0,
             last_column   = len(table_options["columns"]) - 1,
             header_format = header_format,
             cell_format   = cell_format)

worksheet_results.merge_range(first_row   = 0,
                              first_col   = 0,
                              last_row    = 0,
                              last_col    = len(table_options["columns"]) - 1,
                              data        = karting_data["race_name"],
                              cell_format = merge_format)

#############################
# Individual driver results #
#############################
driver_data = set()
fastest_lap = {}
for team_data in karting_data["results"]:
  for lap in team_data["laps"]:
    driver = lap["driver"]
    if driver != "Pit":
      driver_data.add((driver, team_data["team_name"]))
      if driver in fastest_lap:
        fastest_lap[driver] = min(fastest_lap[driver], lap["time"])
      else:
        fastest_lap[driver] = lap["time"]

driver_data = list(driver_data)
driver_data.sort(key = lambda driver : fastest_lap[driver[0]])

driver_position = "INDEX(race_results[Position], MATCH(driver_results[[#This Row], [Team]], race_results[Team], 0))"
team_table_name = f"\"team\" & {driver_position} & \"_results"
driver_laps     = f"IF(INDIRECT({team_table_name}[Driver]\") = driver_results[[#This Row], [Driver]], INDIRECT({team_table_name}[Lap times '[sec']]\"))"

table_options = {"name"    : "driver_results",
                 "data"    : driver_data,
                 "columns" : [{"header"  : "Driver"},
                              {"header"  : "Team"},
                              {"header"  : "Laps [laps]",
                               "formula" : f"=COUNTIF(INDIRECT({team_table_name}[Driver]\"), driver_results[[#This Row], [Driver]])"},
                              {"header"  : "Fastest lap [sec]"},
                              {"header"  : "Slowest lap [sec]"},
                              {"header"  : "Average lap [sec]"},
                              {"header"  : "Avg lap (no outliers) [sec]"},
                              {"header"  : "Standard deviation [sec]"}]}

# Fastest lap formula
first_row = len(total_data) + 7
for i in range(len(driver_data)):
  worksheet_results.write_formula(row     = first_row + i,
                                  col     = 3,
                                  formula = f"{{=MIN({driver_laps})}}")

# Slowest lap formula
for i in range(len(driver_data)):
  worksheet_results.write_formula(row     = first_row + i,
                                  col     = 4,
                                  formula = f"{{=MAX({driver_laps})}}")

# Average lap formula
for i in range(len(driver_data)):
  worksheet_results.write_formula(row     = first_row + i,
                                  col     = 5,
                                  formula = f"{{=AVERAGE({driver_laps})}}")

# Average lap without outliers formula
outliers_row         = first_row - 1
outliers_column      = len(table_options["columns"]) + 1
outliers_column_char = xlsxwriter.utility.xl_col_to_name(outliers_column)
worksheet_results.write_string(row    = outliers_row,
                               col    = outliers_column,
                               string = "Percentage of outliers")
worksheet_results.write_number(row    = outliers_row + 1,
                               col    = outliers_column,
                               number = 0.1)

for i in range(len(driver_data)):
  worksheet_results.write_formula(row     = first_row + i,
                                  col     = 6,
                                  formula = f"{{=AVERAGE(SMALL({driver_laps}, ROW(INDIRECT(\"1:\"&ROUND((1 - ${outliers_column_char}${outliers_row + 2}) * driver_results[[#This Row], [Laps '[laps']]], 0)))))}}")

# Standard deviation formula
for i in range(len(driver_data)):
  worksheet_results.write_formula(row     = first_row + i,
                                  col     = 7,
                                  formula = f"{{=STDEV.S({driver_laps})}}")


create_table(worksheet     = worksheet_results,
             table_options = table_options,
             first_row     = len(total_data) + 6,
             last_row      = len(total_data) + len(driver_data) + 6,
             first_column  = 0,
             last_column   = len(table_options["columns"]) - 1,
             header_format = header_format,
             cell_format   = cell_format)

###########################
# Individual team results #
###########################
for i, team_data in enumerate(karting_data["results"]):

  lap_data = []
  for lap in team_data["laps"]:
    lap_data.append([lap["time"], lap["driver"]])

  table_options = {"name"    : f"team{i + 1}_results",
                   "data"    : lap_data,
                   "columns" : [{"header"  : "Lap times [sec]"},
                                {"header"  : "Driver"},
                                {"header"  : "Running average [sec]",
                                 "formula" : f"=AVERAGE(INDEX(team{i + 1}_results[Lap times '[sec']], 1):team{i + 1}_results[[#This Row], [Lap times '[sec']]])"},
                                {"header"  : "Cumulative time [sec]",
                                 "formula" : f"=SUM(INDEX(team{i + 1}_results[Lap times '[sec']], 1):team{i + 1}_results[[#This Row], [Lap times '[sec']]])"}]}

  first_column = i * (len(table_options["columns"]) + 1)
  last_column  = first_column + len(table_options["columns"]) - 1

  create_table(worksheet     = worksheet_race_data,
               table_options = table_options,
               first_row     = 1,
               last_row      = len(lap_data) + 1,
               first_column  = first_column,
               last_column   = last_column,
               header_format = header_format,
               cell_format   = cell_format)

  worksheet_race_data.merge_range(first_row   = 0,
                                  first_col   = first_column,
                                  last_row    = 0,
                                  last_col    = last_column,
                                  data        = f"=INDEX(race_results[Team], MATCH({i + 1}, race_results[Position], 0))",
                                  cell_format = merge_format)

#######################
# Intermediate points #
#######################
# TODO use HSTACK in the future
for i in range(len(all_cumulative_times)):
  all_cumulative_times[i] = [all_cumulative_times[i]]

table_options = {"name"    : f"intermediate_results",
                 "data"    : all_cumulative_times,
                 "columns" : [{"header"  : "All cumulative times [sec]"}]}

current_time = "intermediate_results[[#This Row], [All cumulative times '[sec']]]"

for i in range(number_of_teams):
  current_time_index           = f"MATCH({current_time}, team{i + 1}_results[Cumulative time '[sec']], 1)"
  corrected_current_time_index = f"IFERROR({current_time_index}, 0)"
  previous_time                = f"INDEX(team{i + 1}_results[Cumulative time '[sec']], {current_time_index})"
  corrected_previous_time      = f"IFERROR({previous_time}, 0)"
  lap_time                     = f"INDEX(team{i + 1}_results[Lap times '[sec']], {corrected_current_time_index} + 1)"
  average_lap_time             = f"INDEX(team{i + 1}_results[Running average '[sec']], {current_time_index})"
  corrected_lap_time           = f"IFERROR({lap_time}, {average_lap_time})"

  formula = f"={corrected_current_time_index} + ({current_time} - {corrected_previous_time}) / {corrected_lap_time}"

  table_options["columns"].append({"header"  : f"Team{i + 1} laps [laps]",
                                   "formula" : formula})

for i in range(number_of_teams):
  current_team_lap = f"intermediate_results[[#This Row], [Team{i + 1} laps '[laps']]]"

  formula = f"=intermediate_results[[#This Row], [Team1 laps '[laps']]] - {current_team_lap}"

  table_options["columns"].append({"header"  : f"Team{i + 1} distance to winner [laps]",
                                   "formula" : formula})

all_team_laps = f"intermediate_results[[#This Row], [Team1 laps '[laps']]:[Team{number_of_teams} laps '[laps']]]"

for i in range(number_of_teams):
  formula = f"=MAX({all_team_laps}) - intermediate_results[[#This Row], [Team{i + 1} laps '[laps']]]"

  table_options["columns"].append({"header"  : f"Team{i + 1} distance to leader [laps]",
                                   "formula" : formula})

formula = f"={number_of_teams} * {current_time} / SUM({all_team_laps})"

table_options["columns"].append({"header"  : f"Total running average [sec]",
                                 "formula" : formula})

for i in range(number_of_teams):
  current_team_lap = f"intermediate_results[[#This Row], [Team{i + 1} laps '[laps']]]"

  formula = f"={current_time} / {current_team_lap} - intermediate_results[[#This Row], [Total running average '[sec']]]"

  table_options["columns"].append({"header"  : f"Team{i + 1} running average diff [sec]",
                                   "formula" : formula})

create_table(worksheet     = worksheet_intermediate,
             table_options = table_options,
             first_row     = 0,
             last_row      = len(all_cumulative_times),
             first_column  = 0,
             last_column   = len(table_options["columns"]) - 1,
             header_format = header_format,
             cell_format   = cell_format)

###########################################
# Add the running average lap times chart #
###########################################
chart = workbook.add_chart({"type"    : "scatter",
                            "subtype" : "straight"})

for i, team_data in enumerate(karting_data["results"]):
  first_column = i * 5

  number_of_laps = len(team_data["laps"])

  chart.add_series({"name"       : ["race_data", 0, first_column],
                    "categories" : ["race_data", 2, first_column + 3, number_of_laps + 1, first_column + 3],
                    "values"     : ["race_data", 2, first_column + 2, number_of_laps + 1, first_column + 2]})

x_major_unit, x_minor_unit = get_race_time_axis_units(total_race_time)

x_max = calc_next_multiple(number   = total_race_time,
                           multiple = x_minor_unit)

y_major_unit = 0.5
y_minor_unit = y_major_unit // 5

max_running_average = 0
for running_average in running_averages.values():
  max_running_average = max(max(running_average), max_running_average)

min_running_average = max_running_average
for running_average in running_averages.values():
  min_running_average = min(min(running_average), min_running_average)

y_max = calc_next_multiple(number   = max_running_average,
                           multiple = y_major_unit)
y_min = calc_previous_multiple(number   = min_running_average,
                               multiple = y_major_unit)

chart.set_title({"name" : "Running average lap times"})
set_default_axis_options(chart        = chart,
                         x_name       = "Time [sec]",
                         x_min        = 0,
                         x_max        = x_max,
                         x_major_unit = x_major_unit,
                         x_minor_unit = x_minor_unit,
                         y_name       = "Average lap time [sec]",
                         y_min        = y_min,
                         y_max        = y_max,
                         y_major_unit = y_major_unit,
                         y_minor_unit = y_minor_unit)
chart.set_size({"x_scale" : 4,
                "y_scale" : 3})

worksheet_results.insert_chart(row   = len(total_data) + len(driver_data) + 10,
                               col   = 0,
                               chart = chart)

############################################
# Add the running distance to winner chart #
############################################
chart = workbook.add_chart({"type"    : "scatter",
                            "subtype" : "straight"})

for i, team_data in enumerate(karting_data["results"]):
  first_column_label = i * 5
  first_column_data  = number_of_teams + 1

  number_of_time_points = len(all_cumulative_times)

  chart.add_series({"name"       : ["race_data", 0, first_column_label],
                    "categories" : ["intermediate_data", 1, 0, number_of_time_points, 0],
                    "values"     : ["intermediate_data", 1, first_column_data + i, number_of_time_points, first_column_data + i]})

x_major_unit, x_minor_unit = get_race_time_axis_units(total_race_time)

x_max = calc_next_multiple(number   = total_race_time,
                           multiple = x_minor_unit)

max_distance_to_winner = 0
min_distance_to_winner = 0
winner_team_name       = karting_data["results"][0]["team_name"]
for team_interpolated_laps in interpolated_laps.values():
  for i, team_interpolated_lap in enumerate(team_interpolated_laps):
    distance_to_winner = interpolated_laps[winner_team_name][i] - team_interpolated_lap
    max_distance_to_winner = max(distance_to_winner, max_distance_to_winner)
    min_distance_to_winner = min(distance_to_winner, min_distance_to_winner)

y_max = calc_next_multiple(number   = max_distance_to_winner,
                           multiple = y_major_unit)
y_min = calc_previous_multiple(number   = min_distance_to_winner,
                               multiple = y_major_unit)

y_major_unit, y_minor_unit = get_laps_axis_units(y_max - y_min)

chart.set_title({"name" : "Running distance to winner"})
set_default_axis_options(chart        = chart,
                         x_name       = "Time [sec]",
                         x_min        = 0,
                         x_max        = x_max,
                         x_major_unit = x_major_unit,
                         x_minor_unit = x_minor_unit,
                         y_name       = "Distance to winner [laps]",
                         y_min        = y_min,
                         y_max        = y_max,
                         y_major_unit = y_major_unit,
                         y_minor_unit = y_minor_unit)
chart.set_size({"x_scale" : 4,
                "y_scale" : 3})

worksheet_results.insert_chart(row   = len(total_data) + len(driver_data) + 56,
                               col   = 0,
                               chart = chart)

############################################
# Add the running distance to leader chart #
############################################
chart = workbook.add_chart({"type"    : "scatter",
                            "subtype" : "straight"})

for i, team_data in enumerate(karting_data["results"]):
  first_column_label = i * 5
  first_column_data  = number_of_teams * 2 + 1

  number_of_time_points = len(all_cumulative_times)

  chart.add_series({"name"       : ["race_data", 0, first_column_label],
                    "categories" : ["intermediate_data", 1, 0, number_of_time_points, 0],
                    "values"     : ["intermediate_data", 1, first_column_data + i, number_of_time_points, first_column_data + i]})

x_major_unit, x_minor_unit = get_race_time_axis_units(total_race_time)

x_max = calc_next_multiple(number   = total_race_time,
                           multiple = x_minor_unit)

max_distance_to_leader = 0
for team_name, team_interpolated_laps in interpolated_laps.items():
  for i, team_interpolated_lap in enumerate(team_interpolated_laps):

    leader_team_name = team_name
    highest_lap      = team_interpolated_lap
    for other_team_name, other_team_interpolated_laps in interpolated_laps.items():
      if other_team_interpolated_laps[i] > highest_lap:
        highest_lap = other_team_interpolated_laps[i]
        leader_team_name = other_team_name

    distance_to_leader = interpolated_laps[leader_team_name][i] - team_interpolated_lap
    max_distance_to_leader = max(distance_to_leader, max_distance_to_leader)

y_max = calc_next_multiple(number   = max_distance_to_leader,
                           multiple = y_major_unit)
y_min = -y_major_unit

y_major_unit, y_minor_unit = get_laps_axis_units(y_max - y_min)

chart.set_title({"name" : "Running distance to leader"})
set_default_axis_options(chart        = chart,
                         x_name       = "Time [sec]",
                         x_min        = 0,
                         x_max        = x_max,
                         x_major_unit = x_major_unit,
                         x_minor_unit = x_minor_unit,
                         y_name       = "Distance to leader [laps]",
                         y_min        = y_min,
                         y_max        = y_max,
                         y_major_unit = y_major_unit,
                         y_minor_unit = y_minor_unit)
chart.set_size({"x_scale" : 4,
                "y_scale" : 3})

worksheet_results.insert_chart(row   = len(total_data) + len(driver_data) + 102,
                               col   = 0,
                               chart = chart)

################################################
# Add the running average lap times diff chart #
################################################
chart = workbook.add_chart({"type"    : "scatter",
                            "subtype" : "straight"})

for i, team_data in enumerate(karting_data["results"]):
  first_column_label = i * 5
  first_column_data  = number_of_teams * 3 + 2

  number_of_time_points = len(all_cumulative_times)

  chart.add_series({"name"       : ["race_data", 0, first_column_label],
                    "categories" : ["intermediate_data", 1, 0, number_of_time_points, 0],
                    "values"     : ["intermediate_data", 1, first_column_data + i, number_of_time_points, first_column_data + i]})

x_major_unit, x_minor_unit = get_race_time_axis_units(total_race_time)

x_max = calc_next_multiple(number   = total_race_time,
                           multiple = x_minor_unit)

max_diff_to_average = 0
min_diff_to_average = 0
for team_total_running_average_diff in total_running_average_diff.values():
  for running_average_diff in team_total_running_average_diff:
    max_diff_to_average = max(running_average_diff, max_diff_to_average)
    min_diff_to_average = min(running_average_diff, min_diff_to_average)

y_max = calc_next_multiple(number   = max_diff_to_average,
                           multiple = y_major_unit)
y_min = calc_previous_multiple(number   = min_diff_to_average,
                               multiple = y_major_unit)

y_major_unit, y_minor_unit = get_laps_axis_units(y_max - y_min)

chart.set_title({"name" : "Diff to total running average lap time"})
set_default_axis_options(chart        = chart,
                         x_name       = "Time [sec]",
                         x_min        = 0,
                         x_max        = x_max,
                         x_major_unit = x_major_unit,
                         x_minor_unit = x_minor_unit,
                         y_name       = "Diff to total average lap time [sec]",
                         y_min        = y_min,
                         y_max        = y_max,
                         y_major_unit = y_major_unit,
                         y_minor_unit = y_minor_unit)
chart.set_size({"x_scale" : 4,
                "y_scale" : 3})

worksheet_results.insert_chart(row   = len(total_data) + len(driver_data) + 148,
                               col   = 0,
                               chart = chart)

###########################
# Generate the Excel file #
###########################
workbook.close()
