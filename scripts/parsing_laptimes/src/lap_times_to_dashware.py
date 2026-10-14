import argparse
import re

#################
# Input parsing #
#################
parser = argparse.ArgumentParser(prog        = "lap_times_to_dashware" ,
                                 description = "Transform lap times into Dashware " +
                                               "CSV data")

parser.add_argument("-i", "--input",
                    required = True,
                    help     = "The input TXT file containing all the karting lap data")
parser.add_argument("-o", "--output",
                    required = True,
                    help     = "The output CSV file containing the Dashware " +
                               "karting data")

args = parser.parse_args()

################
# Data parsing #
################
with open(args.input, 'r') as lap_data_file:
  lap_data_contents = lap_data_file.read()

##########################
# Cleanup the input data #
##########################
lap_data_contents = re.split(" |\t|\n|\r", lap_data_contents.strip())

# We represent the lap times in ms
lap_data = []
for lap_time in lap_data_contents:

  lap_time_parts = lap_time.split(':')

  milliseconds = lap_time_parts[-1]
  milliseconds = milliseconds.replace(',', '')
  milliseconds = milliseconds.replace('.', '')
  milliseconds = int(milliseconds)

  if len(lap_time_parts) > 2:
    minutes = int(lap_time_parts[-2])
    milliseconds += 60_000 * minutes

  lap_data.append(milliseconds)

#######################
# Create the CSV data #
#######################

def lap_time_to_str(lap_time):
  hours = lap_time // (60 * 60 * 1000)
  minutes = (lap_time % (60 * 60 * 1000)) // (60 * 1000)
  seconds = (lap_time % (60 * 1000)) // 1000
  milliseconds = lap_time % 1000

  if hours != 0:
    return f"{hours:02}{minutes:02}:{seconds:02}.{milliseconds:03}"

  if minutes != 0:
    return f"{minutes:02}:{seconds:02}.{milliseconds:03}"

  return f"{seconds:02}.{milliseconds:03}"

csv_contents = "Time, Lap count\n"

running_time = 0
for i, lap_time in enumerate(lap_data):

  csv_contents += f"{lap_time_to_str(running_time)}, {i}\n"
  running_time += lap_time
  csv_contents += f"{lap_time_to_str(running_time - 1)}, {i}\n"

  if i + 1 == len(lap_data):
    csv_contents += f"{lap_time_to_str(running_time)}, {i}\n"

################################
# Write the CSV data to a file #
################################
with open(args.output, "w") as csv_file:
    csv_file.write(csv_contents)
