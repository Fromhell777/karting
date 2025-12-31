import numpy as np

import os
import subprocess
import copy
import argparse
import yaml
import plotly.graph_objects as plotly_go

#################
# Input parsing #
#################
parser = argparse.ArgumentParser(description = "Analyse the karting data and " +
                                               "generate plots.")

parser.add_argument("-i", "--input",
                    required = True,
                    help     = "The input YAML file containing all the karting data")
parser.add_argument("-o", "--output_folder",
                    required = True,
                    help     = "The output directory where the plots will be created")

args = parser.parse_args()

################
# data parsing #
################
with open(args.input) as data_file:
  karting_data = yaml.safe_load(data_file)

##################################################
# Calculate some data out of the karting results #
##################################################
def are_floats_close(lhs, rhs, tolerance = 1e-6):
  return abs(lhs - rhs) <= tolerance

number_of_teams = len(karting_data["results"])

total_race_time = 0
for lap in karting_data["results"][0]["laps"]:
  total_race_time += lap["time"]

lap_drivers = {}
for team_data in karting_data["results"]:
  drivers = [lap["driver"] for lap in team_data["laps"]]
  lap_drivers[team_data["team_name"]] = drivers

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

interpolated_laps = {}
teams_max_cumulative_time_index = {}
for team_name, team_cumulative_times_extended in cumulative_times_extended.items():
  interpolated_laps[team_name] = []
  current_lap_index = 0
  for i, cumulative_time in enumerate(all_cumulative_times):
    while team_cumulative_times_extended[current_lap_index + 1] < cumulative_time:
      current_lap_index += 1

    if cumulative_time > cumulative_times[team_name][-1] and \
       not are_floats_close(cumulative_time, cumulative_times[team_name][-1]):
      if team_name not in teams_max_cumulative_time_index:
        teams_max_cumulative_time_index[team_name] = i - 1

    team_has_stopped = False
    for team_data in karting_data["results"]:
      if team_data["team_name"] == team_name and \
         "has_stopped" in team_data and \
         team_data["has_stopped"]:
        team_has_stopped = True

    if team_has_stopped and \
       (cumulative_times[team_name][-1] < team_cumulative_times_extended[current_lap_index] or
        are_floats_close(cumulative_times[team_name][-1],
                         team_cumulative_times_extended[current_lap_index])):
      # The team has stopped so the laps don't increase anymore
      interpolated_laps[team_name].append(len(cumulative_times[team_name]))
    else:
      # Interpolate
      current_cumulative_time = team_cumulative_times_extended[current_lap_index]
      next_cumulative_time    = team_cumulative_times_extended[current_lap_index + 1]
      interpolated_lap = current_lap_index + (cumulative_time - current_cumulative_time) / \
                                             (next_cumulative_time - current_cumulative_time)
      interpolated_laps[team_name].append(interpolated_lap)

  if team_name not in teams_max_cumulative_time_index:
    teams_max_cumulative_time_index[team_name] = len(all_cumulative_times) - 1

# TODO check
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
# Plots setup #
###############
# Large color palette for maximally distinct colors from all previous colors
# source: https://graphicdesign.stackexchange.com/questions/3682/where-can-i-find-a-large-palette-set-of-contrasting-colors-for-coloring-many-d
color_palette = [
  "#000000", "#FFFF00", "#1CE6FF", "#FF34FF", "#FF4A46", "#008941", "#006FA6", "#A30059",
  "#FFDBE5", "#7A4900", "#0000A6", "#63FFAC", "#B79762", "#004D43", "#8FB0FF", "#997D87",
  "#5A0007", "#809693", "#FEFFE6", "#1B4400", "#4FC601", "#3B5DFF", "#4A3B53", "#FF2F80",
  "#61615A", "#BA0900", "#6B7900", "#00C2A0", "#FFAA92", "#FF90C9", "#B903AA", "#D16100",
  "#DDEFFF", "#000035", "#7B4F4B", "#A1C299", "#300018", "#0AA6D8", "#013349", "#00846F",
  "#372101", "#FFB500", "#C2FFED", "#A079BF", "#CC0744", "#C0B9B2", "#C2FF99", "#001E09",
  "#00489C", "#6F0062", "#0CBD66", "#EEC3FF", "#456D75", "#B77B68", "#7A87A1", "#788D66",
  "#885578", "#FAD09F", "#FF8A9A", "#D157A0", "#BEC459", "#456648", "#0086ED", "#886F4C",

  "#34362D", "#B4A8BD", "#00A6AA", "#452C2C", "#636375", "#A3C8C9", "#FF913F", "#938A81",
  "#575329", "#00FECF", "#B05B6F", "#8CD0FF", "#3B9700", "#04F757", "#C8A1A1", "#1E6E00",
  "#7900D7", "#A77500", "#6367A9", "#A05837", "#6B002C", "#772600", "#D790FF", "#9B9700",
  "#549E79", "#FFF69F", "#201625", "#72418F", "#BC23FF", "#99ADC0", "#3A2465", "#922329",
  "#5B4534", "#FDE8DC", "#404E55", "#0089A3", "#CB7E98", "#A4E804", "#324E72", "#6A3A4C",
  "#83AB58", "#001C1E", "#D1F7CE", "#004B28", "#C8D0F6", "#A3A489", "#806C66", "#222800",
  "#BF5650", "#E83000", "#66796D", "#DA007C", "#FF1A59", "#8ADBB4", "#1E0200", "#5B4E51",
  "#C895C5", "#320033", "#FF6832", "#66E1D3", "#CFCDAC", "#D0AC94", "#7ED379", "#012C58",

  "#7A7BFF", "#D68E01", "#353339", "#78AFA1", "#FEB2C6", "#75797C", "#837393", "#943A4D",
  "#B5F4FF", "#D2DCD5", "#9556BD", "#6A714A", "#001325", "#02525F", "#0AA3F7", "#E98176",
  "#DBD5DD", "#5EBCD1", "#3D4F44", "#7E6405", "#02684E", "#962B75", "#8D8546", "#9695C5",
  "#E773CE", "#D86A78", "#3E89BE", "#CA834E", "#518A87", "#5B113C", "#55813B", "#E704C4",
  "#00005F", "#A97399", "#4B8160", "#59738A", "#FF5DA7", "#F7C9BF", "#643127", "#513A01",
  "#6B94AA", "#51A058", "#A45B02", "#1D1702", "#E20027", "#E7AB63", "#4C6001", "#9C6966",
  "#64547B", "#97979E", "#006A66", "#391406", "#F4D749", "#0045D2", "#006C31", "#DDB6D0",
  "#7C6571", "#9FB2A4", "#00D891", "#15A08A", "#BC65E9", "#FFFFFE", "#C6DC99", "#203B3C",

  "#671190", "#6B3A64", "#F5E1FF", "#FFA0F2", "#CCAA35", "#374527", "#8BB400", "#797868",
  "#C6005A", "#3B000A", "#C86240", "#29607C", "#402334", "#7D5A44", "#CCB87C", "#B88183",
  "#AA5199", "#B5D6C3", "#A38469", "#9F94F0", "#A74571", "#B894A6", "#71BB8C", "#00B433",
  "#789EC9", "#6D80BA", "#953F00", "#5EFF03", "#E4FFFC", "#1BE177", "#BCB1E5", "#76912F",
  "#003109", "#0060CD", "#D20096", "#895563", "#29201D", "#5B3213", "#A76F42", "#89412E",
  "#1A3A2A", "#494B5A", "#A88C85", "#F4ABAA", "#A3F3AB", "#00C6C8", "#EA8B66", "#958A9F",
  "#BDC9D2", "#9FA064", "#BE4700", "#658188", "#83A485", "#453C23", "#47675D", "#3A3F00",
  "#061203", "#DFFB71", "#868E7E", "#98D058", "#6C8F7D", "#D7BFC2", "#3C3E6E", "#D83D66",

  "#2F5D9B", "#6C5E46", "#D25B88", "#5B656C", "#00B57F", "#545C46", "#866097", "#365D25",
  "#252F99", "#00CCFF", "#674E60", "#FC009C", "#92896B"]

# Setup the output directory
os.makedirs(name     = args.output_folder,
            exist_ok = True)


# Generate the docinfo file for the asciidoctor output of the Plotly plots. This
# contains the header needed to be included in the html
with open(os.path.join(args.output_folder, "docinfo.html"), "w") as f:
  f.write("<script src=\"https://cdn.plot.ly/plotly-3.3.0.min.js\"></script>\n")

#####################
## Helper functions #
#####################
def setup_figure_layout(figure,
                        title,
                        x_axis_title,
                        y_axis_title,
                        color_palette):
  figure.update_layout(width       = 1000,
                       height      = 800,
                       title       = {"text"    : title,
                                      "y"       : 0.92,
                                      "x"       : 0.5,
                                      "xanchor" : "center",
                                      "yanchor" : "top"},
                       xaxis_title = x_axis_title,
                       yaxis_title = y_axis_title,
                       colorway    = color_palette)

def make_html(adoc_title,
              info_text,
              figures,
              filename):

  result  = f"= {adoc_title}\n"
  result += ":last-update-label!:\n"
  result += ":icons: font\n"
  result += ":numbered:\n"
  result += ":toc: left\n"
  result += ":prewrap!:\n"
  result += ":docinfo: shared\n\n"

  result += "== Info\n"
  result += f"{info_text}\n\n"

  # Add the Plotly image directly into the html
  result += "== Graphs\n"
  result += "[pass]\n"
  result += "++++\n"

  for figure in figures:
    # Extract html result to embed into html reports
    html_div = figure.to_html(include_plotlyjs = False,
                              full_html        = False)

    result += html_div + "\n"

  result += "++++\n\n"

  with open(filename, "w") as file:
    file.write(result)

  # Generate the HTML from the Asciidoc file
  subprocess.run(args  = ["asciidoctor", filename],
                 check = True)

###########################################
## Add the running average lap times plot #
###########################################
hovertemplate  = "Team: %{fullData.name}<br>"
hovertemplate += "Time: %{x:.3f} sec<br>"
hovertemplate += "Average lap time: %{y:.3f} sec<br>"
hovertemplate += "Driver: %{customdata}"
hovertemplate += "<extra></extra>"

figure_average_lap = plotly_go.Figure()

for team_name, team_running_averages in running_averages.items():
  figure_average_lap.add_trace(plotly_go.Scatter(name          = team_name,
                                                  x             = cumulative_times[team_name],
                                                  y             = team_running_averages,
                                                  customdata    = lap_drivers[team_name],
                                                  hovertemplate = hovertemplate,
                                                  mode          = "lines"))


setup_figure_layout(figure        = figure_average_lap,
                    title         = "Running average lap times",
                    x_axis_title  = "Time [sec]",
                    y_axis_title  = "Average lap time [sec]",
                    color_palette = color_palette)

race_name = karting_data["race_name"]
info_text = f"These are the total karting results of the following race: {race_name}"

################################################
## Add the running distance to the winner plot #
################################################
hovertemplate  = "Team: %{fullData.name}<br>"
hovertemplate += "Time: %{x:.3f} sec<br>"
hovertemplate += "Distance to winner: %{y:.3f} laps<br>"
hovertemplate += "Driver: %{customdata}"
hovertemplate += "<extra></extra>"

figure_winner_distance = plotly_go.Figure()

winner_team_name = karting_data["results"][0]["team_name"]
for team_name, team_interpolated_laps in interpolated_laps.items():
  max_index = teams_max_cumulative_time_index[team_name]

  distance_to_winner         = []
  drivers                    = []
  team_cumulative_time_index = 0
  current_driver             = lap_drivers[team_name][team_cumulative_time_index]
  for i, cumulative_time in enumerate(all_cumulative_times[:max_index + 1]):
    distance_to_winner.append(interpolated_laps[winner_team_name][i] - team_interpolated_laps[i])

    if cumulative_time > cumulative_times[team_name][team_cumulative_time_index] and \
       not are_floats_close(cumulative_time,
                            cumulative_times[team_name][team_cumulative_time_index]):
      team_cumulative_time_index += 1
      current_driver             = lap_drivers[team_name][team_cumulative_time_index]

    drivers.append(current_driver)

  figure_winner_distance.add_trace(plotly_go.Scatter(name          = team_name,
                                                     x             = all_cumulative_times[:max_index + 1],
                                                     y             = distance_to_winner,
                                                     customdata    = drivers,
                                                     hovertemplate = hovertemplate,
                                                     mode          = "lines"))


setup_figure_layout(figure        = figure_winner_distance,
                    title         = "Running distance to winner",
                    x_axis_title  = "Time [sec]",
                    y_axis_title  = "Distance to winner [laps]",
                    color_palette = color_palette)

race_name = karting_data["race_name"]
info_text = f"These are the total karting results of the following race: {race_name}"


#for i, team_data in enumerate(karting_data["results"]):
#  first_column_label = i * 5
#  first_column_data  = number_of_teams + 1
#
#  number_of_time_points = len(all_cumulative_times)
#
#  chart.add_series({"name"       : ["race_data", 0, first_column_label],
#                    "categories" : ["intermediate_data", 1, 0, number_of_time_points, 0],
#                    "values"     : ["intermediate_data", 1, first_column_data + i, number_of_time_points, first_column_data + i]})
#
#x_major_unit, x_minor_unit = get_race_time_axis_units(total_race_time)
#
#x_max = calc_next_multiple(number   = total_race_time,
#                           multiple = x_minor_unit)
#
#max_distance_to_winner = 0
#min_distance_to_winner = 0
#winner_team_name       = karting_data["results"][0]["team_name"]
#for team_interpolated_laps in interpolated_laps.values():
#  for i, team_interpolated_lap in enumerate(team_interpolated_laps):
#    distance_to_winner = interpolated_laps[winner_team_name][i] - team_interpolated_lap
#    max_distance_to_winner = max(distance_to_winner, max_distance_to_winner)
#    min_distance_to_winner = min(distance_to_winner, min_distance_to_winner)



#####################
## Helper functions #
#####################
#def count_drivers(karting_data):
#  drivers = set()
#  for team_data in karting_data["results"]:
#    for lap in team_data["laps"]:
#      if lap["driver"] != "Pit":
#        drivers.add(lap["driver"])
#
#  return len(drivers)
#
#def create_table(worksheet,
#                 table_options,
#                 first_row,
#                 last_row,
#                 first_column,
#                 last_column,
#                 header_format,
#                 cell_format):
#
#  for column in table_options["columns"]:
#    column["format"] = cell_format
#
#  worksheet.add_table(first_row = first_row,
#                      first_col = first_column,
#                      last_row  = last_row,
#                      last_col  = last_column,
#                      options   = table_options)
#
#  headers = [column["header"] for column in table_options["columns"]]
#  for i, header in enumerate(headers):
#    worksheet.write_string(row         = first_row,
#                           col         = first_column + i,
#                           string      = header,
#                           cell_format = header_format)
#
#def calc_next_multiple(number, multiple):
#  return ((number + multiple) // multiple) * multiple
#
#def calc_previous_multiple(number, multiple):
#  return (number // multiple) * multiple
#
#def get_race_time_axis_units(total_race_time):
#  if total_race_time > 5000:
#    major_unit = 1000
#  elif total_race_time > 2500:
#    major_unit = 500
#  elif total_race_time > 1000:
#    major_unit = 250
#  else:
#    major_unit = 100
#
#  minor_unit = major_unit / 5
#
#  return (major_unit, minor_unit)
#
#def get_laps_axis_units(lap_range):
#  if lap_range > 5:
#    major_unit = 0.5
#  elif lap_range > 2.5:
#    major_unit = 0.25
#  elif lap_range > 1:
#    major_unit = 0.125
#  else:
#    major_unit = 0.1
#
#  minor_unit = major_unit / 5
#
#  return (major_unit, minor_unit)
#
#def set_default_axis_options(chart,
#                             x_name,
#                             x_min,
#                             x_max,
#                             x_major_unit,
#                             x_minor_unit,
#                             y_name,
#                             y_min,
#                             y_max,
#                             y_major_unit,
#                             y_minor_unit):
#  chart.set_x_axis({"name"            : x_name,
#                    "min"             : x_min,
#                    "max"             : x_max,
#                    "major_gridlines" : {"visible" : True},
#                    "minor_gridlines" : {"visible" : True},
#                    "major_unit"      : x_major_unit,
#                    "minor_unit"      : x_minor_unit,
#                    "label_position"  : "low"})
#  chart.set_y_axis({"name"            : y_name,
#                    "min"             : y_min,
#                    "max"             : y_max,
#                    "major_gridlines" : {"visible" : True},
#                    "minor_gridlines" : {"visible" : True},
#                    "major_unit"      : y_major_unit,
#                    "minor_unit"      : y_minor_unit,
#                    "label_position"  : "low"})
#
#######################
## Total team results #
#######################
#total_data = []
#for team_data in karting_data["results"]:
#  total_data.append([team_data["finish_position"],
#                     team_data["kart_number"],
#                     team_data["team_name"],
#                     None,
#                     team_data["distance_to_winner"]])
#
#team_table_name = "\"team\" & race_results[[#This Row], [Position]] & \"_results"
#
#table_options = {"name"    : "race_results",
#                 "data"    : total_data,
#                 "columns" : [{"header"  : "Position"},
#                              {"header"  : "Kart number"},
#                              {"header"  : "Team"},
#                              {"header"  : "Laps [laps]",
#                               "formula" : f"=COUNT(INDIRECT({team_table_name}[Lap times '[sec']]\"))"},
#                              {"header"  : "Distance"},
#                              {"header"  : "Fastest lap [laps]",
#                               "formula" : f"=MIN(INDIRECT({team_table_name}[Lap times '[sec']]\"))"},
#                              {"header"  : "Slowest lap [laps]"},
#                              {"header"  : "Average lap [sec]",
#                               "formula" : f"=SUM(INDIRECT({team_table_name}[Lap times '[sec']]\")) / race_results[[#This Row], [Laps '[laps']]]"},
#                              {"header"  : "Standard deviation [sec]"},
#                              {"header"  : "Pit time [sec]",
#                               "formula" : f"=SUMIF(INDIRECT({team_table_name}[Driver]\"), \"Pit\", INDIRECT({team_table_name}[Lap times '[sec']]\"))"},
#                              {"header"  : "Pit stops",
#                               "formula" : f"=COUNTIF(INDIRECT({team_table_name}[Driver]\"), \"Pit\")"},
#                              {"header"  : "Average pit time [sec]",
#                               "formula" : "=race_results[[#This Row], [Pit time '[sec']]] / race_results[[#This Row], [Pit stops]]"}]}
#
## Slowest lap formula
#for i in range(len(total_data)):
#  worksheet_results.write_formula(row     = i + 2,
#                                  col     = 6,
#                                  formula = f"{{=MAX(IF(INDIRECT({team_table_name}[Driver]\") <> \"Pit\", INDIRECT({team_table_name}[Lap times '[sec']]\")))}}")
#
## Standard deviation formula
#for i in range(len(total_data)):
#  worksheet_results.write_formula(row     = i + 2,
#                                  col     = 8,
#                                  formula = f"{{=STDEV.S(IF(INDIRECT({team_table_name}[Driver]\") <> \"Pit\", INDIRECT({team_table_name}[Lap times '[sec']]\")))}}")
#
#create_table(worksheet     = worksheet_results,
#             table_options = table_options,
#             first_row     = 1,
#             last_row      = 1 + len(total_data),
#             first_column  = 0,
#             last_column   = len(table_options["columns"]) - 1,
#             header_format = header_format,
#             cell_format   = cell_format)
#
#worksheet_results.merge_range(first_row   = 0,
#                              first_col   = 0,
#                              last_row    = 0,
#                              last_col    = len(table_options["columns"]) - 1,
#                              data        = karting_data["race_name"],
#                              cell_format = merge_format)
#
##############################
## Individual driver results #
##############################
#driver_data = set()
#fastest_lap = {}
#for team_data in karting_data["results"]:
#  for lap in team_data["laps"]:
#    driver = lap["driver"]
#    if driver != "Pit":
#      driver_data.add((driver, team_data["team_name"]))
#      if driver in fastest_lap:
#        fastest_lap[driver] = min(fastest_lap[driver], lap["time"])
#      else:
#        fastest_lap[driver] = lap["time"]
#
#driver_data = list(driver_data)
#driver_data.sort(key = lambda driver : fastest_lap[driver[0]])
#
#driver_position = "INDEX(race_results[Position], MATCH(driver_results[[#This Row], [Team]], race_results[Team], 0))"
#team_table_name = f"\"team\" & {driver_position} & \"_results"
#driver_laps     = f"IF(INDIRECT({team_table_name}[Driver]\") = driver_results[[#This Row], [Driver]], INDIRECT({team_table_name}[Lap times '[sec']]\"))"
#
#table_options = {"name"    : "driver_results",
#                 "data"    : driver_data,
#                 "columns" : [{"header"  : "Driver"},
#                              {"header"  : "Team"},
#                              {"header"  : "Laps [laps]",
#                               "formula" : f"=COUNTIF(INDIRECT({team_table_name}[Driver]\"), driver_results[[#This Row], [Driver]])"},
#                              {"header"  : "Fastest lap [sec]"},
#                              {"header"  : "Slowest lap [sec]"},
#                              {"header"  : "Average lap [sec]"},
#                              {"header"  : "Avg lap (no outliers) [sec]"},
#                              {"header"  : "Standard deviation [sec]"}]}
#
## Fastest lap formula
#first_row = len(total_data) + 7
#for i in range(len(driver_data)):
#  worksheet_results.write_formula(row     = first_row + i,
#                                  col     = 3,
#                                  formula = f"{{=MIN({driver_laps})}}")
#
## Slowest lap formula
#for i in range(len(driver_data)):
#  worksheet_results.write_formula(row     = first_row + i,
#                                  col     = 4,
#                                  formula = f"{{=MAX({driver_laps})}}")
#
## Average lap formula
#for i in range(len(driver_data)):
#  worksheet_results.write_formula(row     = first_row + i,
#                                  col     = 5,
#                                  formula = f"{{=AVERAGE({driver_laps})}}")
#
## Average lap without outliers formula
#outliers_row         = first_row - 1
#outliers_column      = len(table_options["columns"]) + 1
#outliers_column_char = xlsxwriter.utility.xl_col_to_name(outliers_column)
#worksheet_results.write_string(row    = outliers_row,
#                               col    = outliers_column,
#                               string = "Percentage of outliers")
#worksheet_results.write_number(row    = outliers_row + 1,
#                               col    = outliers_column,
#                               number = 0.1)
#
#for i in range(len(driver_data)):
#  worksheet_results.write_formula(row     = first_row + i,
#                                  col     = 6,
#                                  formula = f"{{=AVERAGE(SMALL({driver_laps}, ROW(INDIRECT(\"1:\"&ROUND((1 - ${outliers_column_char}${outliers_row + 2}) * driver_results[[#This Row], [Laps '[laps']]], 0)))))}}")
#
## Standard deviation formula
#for i in range(len(driver_data)):
#  worksheet_results.write_formula(row     = first_row + i,
#                                  col     = 7,
#                                  formula = f"{{=STDEV.S({driver_laps})}}")
#
#
#create_table(worksheet     = worksheet_results,
#             table_options = table_options,
#             first_row     = len(total_data) + 6,
#             last_row      = len(total_data) + len(driver_data) + 6,
#             first_column  = 0,
#             last_column   = len(table_options["columns"]) - 1,
#             header_format = header_format,
#             cell_format   = cell_format)
#
############################
## Individual team results #
############################
#for i, team_data in enumerate(karting_data["results"]):
#
#  lap_data = []
#  for lap in team_data["laps"]:
#    lap_data.append([lap["time"], lap["driver"]])
#
#  table_options = {"name"    : f"team{i + 1}_results",
#                   "data"    : lap_data,
#                   "columns" : [{"header"  : "Lap times [sec]"},
#                                {"header"  : "Driver"},
#                                {"header"  : "Running average [sec]",
#                                 "formula" : f"=AVERAGE(INDEX(team{i + 1}_results[Lap times '[sec']], 1):team{i + 1}_results[[#This Row], [Lap times '[sec']]])"},
#                                {"header"  : "Cumulative time [sec]",
#                                 "formula" : f"=SUM(INDEX(team{i + 1}_results[Lap times '[sec']], 1):team{i + 1}_results[[#This Row], [Lap times '[sec']]])"}]}
#
#  first_column = i * (len(table_options["columns"]) + 1)
#  last_column  = first_column + len(table_options["columns"]) - 1
#
#  create_table(worksheet     = worksheet_race_data,
#               table_options = table_options,
#               first_row     = 1,
#               last_row      = len(lap_data) + 1,
#               first_column  = first_column,
#               last_column   = last_column,
#               header_format = header_format,
#               cell_format   = cell_format)
#
#  worksheet_race_data.merge_range(first_row   = 0,
#                                  first_col   = first_column,
#                                  last_row    = 0,
#                                  last_col    = last_column,
#                                  data        = f"=INDEX(race_results[Team], MATCH({i + 1}, race_results[Position], 0))",
#                                  cell_format = merge_format)
#
########################
## Intermediate points #
########################
## TODO use HSTACK in the future
#for i in range(len(all_cumulative_times)):
#  all_cumulative_times[i] = [all_cumulative_times[i]]
#
#table_options = {"name"    : f"intermediate_results",
#                 "data"    : all_cumulative_times,
#                 "columns" : [{"header"  : "All cumulative times [sec]"}]}
#
#current_time = "intermediate_results[[#This Row], [All cumulative times '[sec']]]"
#
#for i in range(number_of_teams):
#  current_time_index           = f"MATCH({current_time}, team{i + 1}_results[Cumulative time '[sec']], 1)"
#  corrected_current_time_index = f"IFERROR({current_time_index}, 0)"
#  previous_time                = f"INDEX(team{i + 1}_results[Cumulative time '[sec']], {current_time_index})"
#  corrected_previous_time      = f"IFERROR({previous_time}, 0)"
#  lap_time                     = f"INDEX(team{i + 1}_results[Lap times '[sec']], {corrected_current_time_index} + 1)"
#  average_lap_time             = f"INDEX(team{i + 1}_results[Running average '[sec']], {current_time_index})"
#  corrected_lap_time           = f"IFERROR({lap_time}, {average_lap_time})"
#
#  formula = f"={corrected_current_time_index} + ({current_time} - {corrected_previous_time}) / {corrected_lap_time}"
#
#  table_options["columns"].append({"header"  : f"Team{i + 1} laps [laps]",
#                                   "formula" : formula})
#
#for i in range(number_of_teams):
#  current_team_lap = f"intermediate_results[[#This Row], [Team{i + 1} laps '[laps']]]"
#
#  formula = f"=intermediate_results[[#This Row], [Team1 laps '[laps']]] - {current_team_lap}"
#
#  table_options["columns"].append({"header"  : f"Team{i + 1} distance to winner [laps]",
#                                   "formula" : formula})
#
#all_team_laps = f"intermediate_results[[#This Row], [Team1 laps '[laps']]:[Team{number_of_teams} laps '[laps']]]"
#
#for i in range(number_of_teams):
#  formula = f"=MAX({all_team_laps}) - intermediate_results[[#This Row], [Team{i + 1} laps '[laps']]]"
#
#  table_options["columns"].append({"header"  : f"Team{i + 1} distance to leader [laps]",
#                                   "formula" : formula})
#
#formula = f"={number_of_teams} * {current_time} / SUM({all_team_laps})"
#
#table_options["columns"].append({"header"  : f"Total running average [sec]",
#                                 "formula" : formula})
#
#for i in range(number_of_teams):
#  current_team_lap = f"intermediate_results[[#This Row], [Team{i + 1} laps '[laps']]]"
#
#  formula = f"={current_time} / {current_team_lap} - intermediate_results[[#This Row], [Total running average '[sec']]]"
#
#  table_options["columns"].append({"header"  : f"Team{i + 1} running average diff [sec]",
#                                   "formula" : formula})
#
#create_table(worksheet     = worksheet_intermediate,
#             table_options = table_options,
#             first_row     = 0,
#             last_row      = len(all_cumulative_times),
#             first_column  = 0,
#             last_column   = len(table_options["columns"]) - 1,
#             header_format = header_format,
#             cell_format   = cell_format)
#
#############################################
## Add the running distance to winner chart #
#############################################
#chart = workbook.add_chart({"type"    : "scatter",
#                            "subtype" : "smooth"})
#
#for i, team_data in enumerate(karting_data["results"]):
#  first_column_label = i * 5
#  first_column_data  = number_of_teams + 1
#
#  number_of_time_points = len(all_cumulative_times)
#
#  chart.add_series({"name"       : ["race_data", 0, first_column_label],
#                    "categories" : ["intermediate_data", 1, 0, number_of_time_points, 0],
#                    "values"     : ["intermediate_data", 1, first_column_data + i, number_of_time_points, first_column_data + i]})
#
#x_major_unit, x_minor_unit = get_race_time_axis_units(total_race_time)
#
#x_max = calc_next_multiple(number   = total_race_time,
#                           multiple = x_minor_unit)
#
#max_distance_to_winner = 0
#min_distance_to_winner = 0
#winner_team_name       = karting_data["results"][0]["team_name"]
#for team_interpolated_laps in interpolated_laps.values():
#  for i, team_interpolated_lap in enumerate(team_interpolated_laps):
#    distance_to_winner = interpolated_laps[winner_team_name][i] - team_interpolated_lap
#    max_distance_to_winner = max(distance_to_winner, max_distance_to_winner)
#    min_distance_to_winner = min(distance_to_winner, min_distance_to_winner)
#
#y_max = calc_next_multiple(number   = max_distance_to_winner,
#                           multiple = y_major_unit)
#y_min = calc_previous_multiple(number   = min_distance_to_winner,
#                               multiple = y_major_unit)
#
#y_major_unit, y_minor_unit = get_laps_axis_units(y_max - y_min)
#
#chart.set_title({"name" : "Running distance to winner"})
#set_default_axis_options(chart        = chart,
#                         x_name       = "Time [sec]",
#                         x_min        = 0,
#                         x_max        = x_max,
#                         x_major_unit = x_major_unit,
#                         x_minor_unit = x_minor_unit,
#                         y_name       = "Distance to winner [laps]",
#                         y_min        = y_min,
#                         y_max        = y_max,
#                         y_major_unit = y_major_unit,
#                         y_minor_unit = y_minor_unit)
#chart.set_size({"x_scale" : 4,
#                "y_scale" : 3})
#
#worksheet_results.insert_chart(row   = len(total_data) + len(driver_data) + 56,
#                               col   = 0,
#                               chart = chart)
#
#############################################
## Add the running distance to leader chart #
#############################################
#chart = workbook.add_chart({"type"    : "scatter",
#                            "subtype" : "smooth"})
#
#for i, team_data in enumerate(karting_data["results"]):
#  first_column_label = i * 5
#  first_column_data  = number_of_teams * 2 + 1
#
#  number_of_time_points = len(all_cumulative_times)
#
#  chart.add_series({"name"       : ["race_data", 0, first_column_label],
#                    "categories" : ["intermediate_data", 1, 0, number_of_time_points, 0],
#                    "values"     : ["intermediate_data", 1, first_column_data + i, number_of_time_points, first_column_data + i]})
#
#x_major_unit, x_minor_unit = get_race_time_axis_units(total_race_time)
#
#x_max = calc_next_multiple(number   = total_race_time,
#                           multiple = x_minor_unit)
#
#max_distance_to_leader = 0
#for team_name, team_interpolated_laps in interpolated_laps.items():
#  for i, team_interpolated_lap in enumerate(team_interpolated_laps):
#
#    leader_team_name = team_name
#    highest_lap      = team_interpolated_lap
#    for other_team_name, other_team_interpolated_laps in interpolated_laps.items():
#      if other_team_interpolated_laps[i] > highest_lap:
#        highest_lap = other_team_interpolated_laps[i]
#        leader_team_name = other_team_name
#
#    distance_to_leader = interpolated_laps[leader_team_name][i] - team_interpolated_lap
#    max_distance_to_leader = max(distance_to_leader, max_distance_to_leader)
#
#y_max = calc_next_multiple(number   = max_distance_to_leader,
#                           multiple = y_major_unit)
#y_min = -y_major_unit
#
#y_major_unit, y_minor_unit = get_laps_axis_units(y_max - y_min)
#
#chart.set_title({"name" : "Running distance to leader"})
#set_default_axis_options(chart        = chart,
#                         x_name       = "Time [sec]",
#                         x_min        = 0,
#                         x_max        = x_max,
#                         x_major_unit = x_major_unit,
#                         x_minor_unit = x_minor_unit,
#                         y_name       = "Distance to leader [laps]",
#                         y_min        = y_min,
#                         y_max        = y_max,
#                         y_major_unit = y_major_unit,
#                         y_minor_unit = y_minor_unit)
#chart.set_size({"x_scale" : 4,
#                "y_scale" : 3})
#
#worksheet_results.insert_chart(row   = len(total_data) + len(driver_data) + 102,
#                               col   = 0,
#                               chart = chart)
#
#################################################
## Add the running average lap times diff chart #
#################################################
#chart = workbook.add_chart({"type"    : "scatter",
#                            "subtype" : "smooth"})
#
#for i, team_data in enumerate(karting_data["results"]):
#  first_column_label = i * 5
#  first_column_data  = number_of_teams * 3 + 2
#
#  number_of_time_points = len(all_cumulative_times)
#
#  chart.add_series({"name"       : ["race_data", 0, first_column_label],
#                    "categories" : ["intermediate_data", 1, 0, number_of_time_points, 0],
#                    "values"     : ["intermediate_data", 1, first_column_data + i, number_of_time_points, first_column_data + i]})
#
#x_major_unit, x_minor_unit = get_race_time_axis_units(total_race_time)
#
#x_max = calc_next_multiple(number   = total_race_time,
#                           multiple = x_minor_unit)
#
#max_diff_to_average = 0
#min_diff_to_average = 0
#for team_total_running_average_diff in total_running_average_diff.values():
#  for running_average_diff in team_total_running_average_diff:
#    max_diff_to_average = max(running_average_diff, max_diff_to_average)
#    min_diff_to_average = min(running_average_diff, min_diff_to_average)
#
#y_max = calc_next_multiple(number   = max_diff_to_average,
#                           multiple = y_major_unit)
#y_min = calc_previous_multiple(number   = min_diff_to_average,
#                               multiple = y_major_unit)
#
#y_major_unit, y_minor_unit = get_laps_axis_units(y_max - y_min)
#
#chart.set_title({"name" : "Diff to total running average lap time"})
#set_default_axis_options(chart        = chart,
#                         x_name       = "Time [sec]",
#                         x_min        = 0,
#                         x_max        = x_max,
#                         x_major_unit = x_major_unit,
#                         x_minor_unit = x_minor_unit,
#                         y_name       = "Diff to total average lap time [sec]",
#                         y_min        = y_min,
#                         y_max        = y_max,
#                         y_major_unit = y_major_unit,
#                         y_minor_unit = y_minor_unit)
#chart.set_size({"x_scale" : 4,
#                "y_scale" : 3})
#
#worksheet_results.insert_chart(row   = len(total_data) + len(driver_data) + 148,
#                               col   = 0,
#                               chart = chart)

###########################
# Generate the HTML files #
###########################
make_html(adoc_title = "Total karting results",
          info_text  = info_text,
          figures    = [figure_average_lap, figure_winner_distance],
          filename   = os.path.join(args.output_folder, "total_karting_results.adoc"))

# TODO
# Graph of team average lap time over the cumulative time
# Graph of the distance to winner over the cumulative time
# Graph of the distance to leader over the cumulative time
# Graph of the diff to the total avergage laps over the cumulative time
# Graph of the average lap times of a person over the person cumulative time
# Graph of the average lap times of a person to the fasted driver over the person cumulative time
# Graph of the average lap time diff of a person to the average total person over the person cumulative time
