import numpy as np

import os
import subprocess
import copy
import argparse
import yaml
import plotly.graph_objects as plotly_go
import pandas
import bar_chart_race
import bisect

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
with open(args.input, 'r') as data_file:
  karting_data = yaml.safe_load(data_file)

##################################################
# Calculate some data out of the karting results #
##################################################
def are_floats_close(lhs, rhs, tolerance = 1e-6):
  return abs(lhs - rhs) <= tolerance

number_of_teams = len(karting_data["results"])

team_has_stopped = {}
for team_data in karting_data["results"]:
  team_has_stopped[team_data["team_name"]] = False
  if "has_stopped" in team_data and team_data["has_stopped"]:
    team_has_stopped[team_data["team_name"]] = True

lap_times = {}
for team_data in karting_data["results"]:
  times = [lap["time"] for lap in team_data["laps"]]
  lap_times[team_data["team_name"]] = times

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

    if team_has_stopped[team_name] and \
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

total_running_average = []
for i, cumulative_time in enumerate(all_cumulative_times):
  sum_team_laps       = 0
  sum_cumulative_time = 0
  for team_name, team_interpolated_laps in interpolated_laps.items():
    max_index = teams_max_cumulative_time_index[team_name]

    # We only sum the valid laps and not the one after a team has stopped
    if i <= max_index or not team_has_stopped[team_name]:
      sum_team_laps       += team_interpolated_laps[i]
      sum_cumulative_time += cumulative_time
    else:
      sum_team_laps       += team_interpolated_laps[max_index]
      sum_cumulative_time += all_cumulative_times[max_index]

  total_running_average.append(sum_cumulative_time / sum_team_laps)

total_running_average_diff = {}
for team_name in cumulative_times:
  total_running_average_diff[team_name] = []
  for i, cumulative_time in enumerate(all_cumulative_times):
    total_running_average_diff[team_name].append(cumulative_time / interpolated_laps[team_name][i] -
                                                 total_running_average[i])

# We assume that the driver only rides for one team
all_drivers = set()
for team_data in karting_data["results"]:
  for lap in team_data["laps"]:
    driver_name = lap["driver"]

    if driver_name == "Pit":
      continue

    all_drivers.add(driver_name)

all_drivers = list(all_drivers)
all_drivers.sort()

number_of_drivers = len(all_drivers)

lap_per_drivers = {driver : [] for driver in all_drivers}
for team_data in karting_data["results"]:
  for lap in team_data["laps"]:
    driver_name = lap["driver"]

    if driver_name == "Pit":
      continue

    if driver_name not in lap_per_drivers:
      lap_per_drivers[driver_name] = []

    lap_per_drivers[driver_name].append(lap["time"])

cumulative_times_per_driver = {driver : [] for driver in all_drivers}
for driver_name, driver_lap_times in lap_per_drivers.items():
  cumulative_times_per_driver[driver_name] = np.cumsum(driver_lap_times)

running_averages_per_driver = {driver : [] for driver in all_drivers}
for driver_name, driver_lap_times in lap_per_drivers.items():
  cumulative_time = cumulative_times_per_driver[driver_name]
  running_averages_per_driver[driver_name] = cumulative_time / np.arange(1, len(cumulative_time) + 1)

# Calculate interpolated running averages per driver
all_cumulative_times_driver = []
for driver_cumulative_times in cumulative_times_per_driver.values():
  all_cumulative_times_driver.extend(driver_cumulative_times)

all_cumulative_times_driver.sort()

interpolated_running_averages_per_driver = {driver : [] for driver in all_drivers}
drivers_max_cumulative_time_index = {}
for driver_name, driver_running_averages in running_averages_per_driver.items():

  driver_cumulative_times = cumulative_times_per_driver[driver_name]
  driver_running_averages = running_averages_per_driver[driver_name]

  current_lap_index = 0
  for i, cumulative_time in enumerate(all_cumulative_times_driver):

    while current_lap_index + 1 < len(driver_cumulative_times) and \
          driver_cumulative_times[current_lap_index + 1] < cumulative_time:
      current_lap_index += 1

    if current_lap_index == len(driver_cumulative_times) - 1:
      interpolated_running_average = driver_running_averages[-1]

      if driver_name not in drivers_max_cumulative_time_index:
        drivers_max_cumulative_time_index[driver_name] = i - 1

    elif cumulative_time < driver_cumulative_times[current_lap_index]:

      # We assume that the driver started out with the same running average as
      # at his first measured lap
      interpolated_running_average = driver_running_averages[0]

    else:
      # Interpolate
      current_cumulative_time = driver_cumulative_times[current_lap_index]
      next_cumulative_time    = driver_cumulative_times[current_lap_index + 1]
      current_running_average = driver_running_averages[current_lap_index]
      next_running_average    = driver_running_averages[current_lap_index + 1]
      interpolated_running_average = \
        current_running_average + \
        (cumulative_time - current_cumulative_time) * \
        (next_running_average - current_running_average) / \
        (next_cumulative_time - current_cumulative_time)

    interpolated_running_averages_per_driver[driver_name].append(interpolated_running_average)

  if driver_name not in drivers_max_cumulative_time_index:
    drivers_max_cumulative_time_index[driver_name] = len(all_cumulative_times_driver) - 1

# Calculate interpolated laps per driver
interpolated_laps_per_driver = {driver : [] for driver in all_drivers}
for driver_name, driver_cumulative_times in cumulative_times_per_driver.items():

  current_lap_index = 0
  for i, cumulative_time in enumerate(all_cumulative_times_driver):
    while current_lap_index + 1 < len(driver_cumulative_times) and \
          driver_cumulative_times[current_lap_index + 1] < cumulative_time:
      current_lap_index += 1

    if current_lap_index == len(driver_cumulative_times) - 1:

      # The driver did not ride anymore laps than this so the laps don't
      # increase anymore
      interpolated_lap = len(cumulative_times_per_driver[driver_name])

    elif cumulative_time < driver_cumulative_times[current_lap_index]:

      # Interpolate but we add an extra point where the driver has riden 0 laps
      # at time 0. This is for a more correct interpolation
      next_cumulative_time = driver_cumulative_times[0]
      interpolated_lap = cumulative_time / next_cumulative_time

    else:
      # Interpolate
      current_cumulative_time = driver_cumulative_times[current_lap_index]
      next_cumulative_time    = driver_cumulative_times[current_lap_index + 1]
      interpolated_lap = current_lap_index + 1 + (cumulative_time - current_cumulative_time) / \
                                                 (next_cumulative_time - current_cumulative_time)

    interpolated_laps_per_driver[driver_name].append(interpolated_lap)

total_running_average_driver = []
for i, cumulative_time in enumerate(all_cumulative_times_driver):
  sum_driver_laps     = 0
  sum_cumulative_time = 0
  for driver_name, driver_interpolated_laps in interpolated_laps_per_driver.items():
    max_index = drivers_max_cumulative_time_index[driver_name]

    # We only sum the laps that the driver has actually driven
    if i <= max_index:
      sum_driver_laps     += driver_interpolated_laps[i]
      sum_cumulative_time += cumulative_time
    else:
      sum_driver_laps     += driver_interpolated_laps[max_index]
      sum_cumulative_time += all_cumulative_times_driver[max_index]

  total_running_average_driver.append(sum_cumulative_time / sum_driver_laps)

total_running_average_diff_driver = {driver : [] for driver in all_drivers}
for driver_name in cumulative_times_per_driver:
  for i, cumulative_time in enumerate(all_cumulative_times_driver):
    total_running_average_diff_driver[driver_name].append(cumulative_time / interpolated_laps_per_driver[driver_name][i] -
                                                          total_running_average_driver[i])

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
docinfo_filename = os.path.join(args.output_folder, "docinfo.html")
with open(docinfo_filename, 'w') as docinfo_file:
  docinfo_file.write("<script src=\"https://cdn.plot.ly/plotly-3.3.0.min.js\"></script>\n")

####################
# Helper functions #
####################
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

  # Remove the Asciidoc file
  os.remove(filename)

##########################
# Add the lap times plot #
##########################
hovertemplate  = "Team: %{fullData.name}<br>"
hovertemplate += "Time: %{x:.3f} sec<br>"
hovertemplate += "Lap time: %{y:.3f} sec<br>"
hovertemplate += "Driver: %{customdata}"
hovertemplate += "<extra></extra>"

figure_lap_times = plotly_go.Figure()

for team_name, team_lap_times in lap_times.items():
  figure_lap_times.add_trace(plotly_go.Scatter(name          = team_name,
                                               x             = cumulative_times[team_name],
                                               y             = team_lap_times,
                                               customdata    = lap_drivers[team_name],
                                               hovertemplate = hovertemplate,
                                               mode          = "lines"))

setup_figure_layout(figure        = figure_lap_times,
                    title         = "Lap times",
                    x_axis_title  = "Time [sec]",
                    y_axis_title  = "Lap time [sec]",
                    color_palette = color_palette)

##########################################
# Add the running average lap times plot #
##########################################
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

###############################################
# Add the running distance to the winner plot #
###############################################
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

###############################################
# Add the running distance to the leader plot #
###############################################
hovertemplate  = "Team: %{fullData.name}<br>"
hovertemplate += "Time: %{x:.3f} sec<br>"
hovertemplate += "Distance to leader: %{y:.3f} laps<br>"
hovertemplate += "Driver: %{customdata}"
hovertemplate += "<extra></extra>"

figure_leader_distance = plotly_go.Figure()

for team_name, team_interpolated_laps in interpolated_laps.items():
  max_index = teams_max_cumulative_time_index[team_name]

  distance_to_leader         = []
  drivers                    = []
  team_cumulative_time_index = 0
  current_driver             = lap_drivers[team_name][team_cumulative_time_index]
  for i, cumulative_time in enumerate(all_cumulative_times[:max_index + 1]):
    leader_team_name = team_name
    highest_lap      = interpolated_laps[team_name][i]
    for other_team_name, other_team_interpolated_laps in interpolated_laps.items():
      if other_team_interpolated_laps[i] > highest_lap:
        highest_lap = other_team_interpolated_laps[i]
        leader_team_name = other_team_name

    distance_to_leader.append(interpolated_laps[leader_team_name][i] - team_interpolated_laps[i])

    if cumulative_time > cumulative_times[team_name][team_cumulative_time_index] and \
       not are_floats_close(cumulative_time,
                            cumulative_times[team_name][team_cumulative_time_index]):
      team_cumulative_time_index += 1
      current_driver             = lap_drivers[team_name][team_cumulative_time_index]

    drivers.append(current_driver)

  figure_leader_distance.add_trace(plotly_go.Scatter(name          = team_name,
                                                     x             = all_cumulative_times[:max_index + 1],
                                                     y             = distance_to_leader,
                                                     customdata    = drivers,
                                                     hovertemplate = hovertemplate,
                                                     mode          = "lines"))

setup_figure_layout(figure        = figure_leader_distance,
                    title         = "Running distance to leader",
                    x_axis_title  = "Time [sec]",
                    y_axis_title  = "Distance to leader [laps]",
                    color_palette = color_palette)

###############################################
# Add the running average lap times diff plot #
###############################################
hovertemplate  = "Team: %{fullData.name}<br>"
hovertemplate += "Time: %{x:.3f} sec<br>"
hovertemplate += "Diff to total average lap time: %{y:.3f} [sec]<br>"
hovertemplate += "Driver: %{customdata}"
hovertemplate += "<extra></extra>"

figure_average_diff = plotly_go.Figure()

for team_name in interpolated_laps.keys():
  max_index = teams_max_cumulative_time_index[team_name]

  drivers                    = []
  team_cumulative_time_index = 0
  current_driver             = lap_drivers[team_name][team_cumulative_time_index]
  for i, cumulative_time in enumerate(all_cumulative_times[:max_index + 1]):
    if cumulative_time > cumulative_times[team_name][team_cumulative_time_index] and \
       not are_floats_close(cumulative_time,
                            cumulative_times[team_name][team_cumulative_time_index]):
      team_cumulative_time_index += 1
      current_driver             = lap_drivers[team_name][team_cumulative_time_index]

    drivers.append(current_driver)

  figure_average_diff.add_trace(plotly_go.Scatter(name          = team_name,
                                                  x             = all_cumulative_times[:max_index + 1],
                                                  y             = total_running_average_diff[team_name][:max_index + 1],
                                                  customdata    = drivers,
                                                  hovertemplate = hovertemplate,
                                                  mode          = "lines"))

setup_figure_layout(figure        = figure_average_diff,
                    title         = "Diff to total running average lap time",
                    x_axis_title  = "Time [sec]",
                    y_axis_title  = "Diff to total average lap time [sec]",
                    color_palette = color_palette)

#####################################
# Add the lap times per driver plot #
#####################################
hovertemplate  = "Driver: %{fullData.name}<br>"
hovertemplate += "Time: %{x:.3f} sec<br>"
hovertemplate += "Lap time: %{y:.3f} sec<br>"
hovertemplate += "<extra></extra>"

figure_driver_lap_times = plotly_go.Figure()

for driver_name, driver_lap_times in lap_per_drivers.items():
  figure_driver_lap_times.add_trace(plotly_go.Scatter(name          = driver_name,
                                                      x             = cumulative_times_per_driver[driver_name],
                                                      y             = driver_lap_times,
                                                      hovertemplate = hovertemplate,
                                                      mode          = "lines"))

setup_figure_layout(figure        = figure_driver_lap_times,
                    title         = "Lap times",
                    x_axis_title  = "Time [sec]",
                    y_axis_title  = "Lap time [sec]",
                    color_palette = color_palette)

############################################################
# Add the lap times per driver plot aligned with race time #
############################################################
hovertemplate  = "Driver: %{fullData.name}<br>"
hovertemplate += "Time: %{x:.3f} sec<br>"
hovertemplate += "Lap time: %{y:.3f} sec<br>"
hovertemplate += "<extra></extra>"

figure_driver_lap_times_aligned = plotly_go.Figure()

driver_colors = {}
driver_rank   = {}
for i, driver_name in enumerate(all_drivers):
  driver_rank[driver_name]   = i
  driver_colors[driver_name] = color_palette[i]

drivers_already_traced = set()
for team_name, team_lap_times in lap_times.items():
  team_cumulative_times = cumulative_times[team_name]
  team_lap_drivers      = lap_drivers[team_name]

  start_index = 0
  end_index   = 0
  driver_name = team_lap_drivers[start_index]
  while end_index < len(team_lap_times):
    if driver_name != team_lap_drivers[end_index] or \
       end_index + 1 == len(team_lap_times):
      if driver_name != "Pit":
        show_legend = True
        if driver_name in drivers_already_traced:
          show_legend = False

        color = driver_colors[driver_name]
        rank  = driver_rank[driver_name]

        figure_driver_lap_times_aligned.add_trace(plotly_go.Scatter(name          = driver_name,
                                                                    x             = team_cumulative_times[start_index:end_index],
                                                                    y             = team_lap_times[start_index:end_index],
                                                                    hovertemplate = hovertemplate,
                                                                    mode          = "lines",
                                                                    line          = {"color" : color},
                                                                    legendgroup   = driver_name,
                                                                    legendrank    = rank,
                                                                    showlegend    = show_legend))

        drivers_already_traced.add(driver_name)

      driver_name = team_lap_drivers[end_index]
      start_index = end_index

    end_index += 1

setup_figure_layout(figure        = figure_driver_lap_times_aligned,
                    title         = "Lap times aligned with the race time",
                    x_axis_title  = "Time [sec]",
                    y_axis_title  = "Lap time [sec]",
                    color_palette = color_palette)

#####################################################
# Add the running average lap times per driver plot #
#####################################################
hovertemplate  = "Driver: %{fullData.name}<br>"
hovertemplate += "Time: %{x:.3f} sec<br>"
hovertemplate += "Average lap time: %{y:.3f} sec<br>"
hovertemplate += "<extra></extra>"

figure_driver_average_lap = plotly_go.Figure()

for driver_name, driver_running_averages in running_averages_per_driver.items():
  figure_driver_average_lap.add_trace(plotly_go.Scatter(name          = driver_name,
                                                        x             = cumulative_times_per_driver[driver_name],
                                                        y             = driver_running_averages,
                                                        hovertemplate = hovertemplate,
                                                        mode          = "lines"))

setup_figure_layout(figure        = figure_driver_average_lap,
                    title         = "Running average lap times",
                    x_axis_title  = "Time [sec]",
                    y_axis_title  = "Average lap time [sec]",
                    color_palette = color_palette)

############################################################
# Add the running average diff with the faster driver plot #
############################################################
hovertemplate  = "Driver: %{fullData.name}<br>"
hovertemplate += "Time: %{x:.3f} sec<br>"
hovertemplate += "Diff with fastest driver: %{y:.3f} sec<br>"
hovertemplate += "<extra></extra>"

figure_fastest_driver_diff = plotly_go.Figure()

fastest_driver_name = all_drivers[0]
fastest_average     = running_averages_per_driver[fastest_driver_name][-1]
for driver_name, driver_running_average in running_averages_per_driver.items():
  if driver_running_average[-1] < fastest_average:
    fastest_driver_name = driver_name
    fastest_average     = driver_running_average[-1]

for driver_name, driver_interpolated_running_averages in interpolated_running_averages_per_driver.items():
  max_index = drivers_max_cumulative_time_index[driver_name]

  diff_to_fastest_driver = []
  for i, cumulative_time in enumerate(all_cumulative_times_driver[:max_index + 1]):
    diff_to_fastest_driver.append(driver_interpolated_running_averages[i] -
                                  interpolated_running_averages_per_driver[fastest_driver_name][i])

  figure_fastest_driver_diff.add_trace(plotly_go.Scatter(name          = driver_name,
                                                         x             = all_cumulative_times_driver[:max_index + 1],
                                                         y             = diff_to_fastest_driver,
                                                         hovertemplate = hovertemplate,
                                                         mode          = "lines"))

setup_figure_layout(figure        = figure_fastest_driver_diff,
                    title         = "Running average diff to the fastest driver",
                    x_axis_title  = "Time [sec]",
                    y_axis_title  = "Diff with the fastest driver [sec]",
                    color_palette = color_palette)

###################################################################
# Add the running average diff with the total average driver plot #
###################################################################
hovertemplate  = "Driver: %{fullData.name}<br>"
hovertemplate += "Time: %{x:.3f} sec<br>"
hovertemplate += "Diff with total average driver: %{y:.3f} sec<br>"
hovertemplate += "<extra></extra>"

figure_average_driver_diff = plotly_go.Figure()

for driver_name, driver_interpolated_laps in interpolated_laps_per_driver.items():
  max_index = drivers_max_cumulative_time_index[driver_name]

  figure_average_driver_diff.add_trace(plotly_go.Scatter(name          = driver_name,
                                                         x             = all_cumulative_times_driver[:max_index + 1],
                                                         y             = total_running_average_diff_driver[driver_name][:max_index + 1],
                                                         hovertemplate = hovertemplate,
                                                         mode          = "lines"))

setup_figure_layout(figure        = figure_average_driver_diff,
                    title         = "Diff with the total running average driver",
                    x_axis_title  = "Time [sec]",
                    y_axis_title  = "Diff with the total average driver [sec]",
                    color_palette = color_palette)

###########################
# Generate the HTML files #
###########################
race_name = karting_data["race_name"]
info_text = f"These are the total karting results of the following race: {race_name}"
make_html(adoc_title = "Total karting results",
          info_text  = info_text,
          figures    = [figure_lap_times,
                        figure_average_lap,
                        figure_winner_distance,
                        figure_leader_distance,
                        figure_average_diff],
          filename   = os.path.join(args.output_folder, "total_karting_results.adoc"))

info_text = f"These are the individual driver karting results of the following race: {race_name}"
make_html(adoc_title = "Driver karting results",
          info_text  = info_text,
          figures    = [figure_driver_lap_times,
                        figure_driver_average_lap,
                        figure_driver_lap_times_aligned,
                        figure_fastest_driver_diff,
                        figure_average_driver_diff],
          filename   = os.path.join(args.output_folder, "driver_karting_results.adoc"))

################
# Some cleanup #
################
# Remove the docinfo file
os.remove(docinfo_filename)

###############################
# Generate the bar-chart-race #
###############################
number_of_points = 120

# Setup the initial team order
initial_team_order = [team_name for team_name in interpolated_laps.keys()]
initial_team_order.sort(key     = lambda team_name: interpolated_laps[team_name][0],
                        reverse = True)

# Add the starting lap of 0 to all the interpolated data
all_cumulative_times.insert(0, 0)
for team_name in interpolated_laps.keys():
  interpolated_laps[team_name].insert(0, 0)

# Create the display data with equidistant points
# We insert a very small start value so the bars show up at the start
interpolated_laps_display = {team_name : [1e-6] for team_name in initial_team_order}
cumulative_times_display  = np.linspace(start = 0,
                                        stop  = all_cumulative_times[-1],
                                        num   = number_of_points)
for team_name, team_interpolated_laps in interpolated_laps.items():

  current_index = 0
  for cumulative_time in cumulative_times_display[1:]:

    while current_index + 1 < len(all_cumulative_times) and \
        all_cumulative_times[current_index + 1] < cumulative_time:
      current_index += 1

    # Interpolate
    current_lap             = team_interpolated_laps[current_index]
    next_lap                = team_interpolated_laps[current_index + 1]
    current_cumulative_time = all_cumulative_times[current_index]
    next_cumulative_time    = all_cumulative_times[current_index + 1]
    interpolated_lap = current_lap + \
                       (cumulative_time - current_cumulative_time) * \
                       (next_lap - current_lap) / \
                       (next_cumulative_time - current_cumulative_time)
    interpolated_laps_display[team_name].append(interpolated_lap)

bar_chart_race_data = pandas.DataFrame(data  = interpolated_laps_display,
                                       index = cumulative_times_display)

def get_bar_text(current_lap, team_name, lap_drivers):
  lap_index = int(current_lap)

  if are_floats_close(current_lap, lap_index):
    lap_index -= 1

  lap_index = max(lap_index, 0)
  lap_index = min(lap_index, len(lap_drivers[team_name]) - 1)

  return f"{current_lap:.2f}\n{lap_drivers[team_name][lap_index]}"

bar_chart_race.bar_chart_race(df                 = bar_chart_race_data,
                              filename           = os.path.join(args.output_folder, "bar_chart_race.mp4"),
                              title              = "Race results",
                              tick_template      = "{x:.2f}",
                              tick_label         = "Total laps [laps]",
                              bar_texttemplate   = get_bar_text,
                              customdata         = lap_drivers,
                              interpolate_period = True,
                              period_template    = "Time: {x:.0f} sec")
