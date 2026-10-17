import argparse
import re
import numpy as np

#################
# Input parsing #
#################
parser = argparse.ArgumentParser(prog        = "lap_times_to_youtube_description" ,
                                 description = "Transform lap times into Youtube " +
                                               "description string")

parser.add_argument("-i", "--input",
                    required = True,
                    help     = "The input TXT file containing all the karting lap data")
parser.add_argument("-f", "--format",
                    default = "default",
                    const = "default",
                    nargs = '?',
                    choices = ("default", "with_sectors", "wik"),
                    help = "The format for input")
parser.add_argument("-s", "--start_time",
                    required = True,
                    help = "The start time of the first counted lap in the video." +
                           "The formats are 'MM:SS' or 'HH:MM:SS'")

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
lap_data_contents = [x for x in lap_data_contents if x != ""]

# These are probably lap numbers instead of lap times
lap_data_contents = [x for x in lap_data_contents if len(x) > 3]

# We represent the lap times in ms
lap_data = []
for lap_time in lap_data_contents:

  lap_time_parts = lap_time.split(':')

  milliseconds = lap_time_parts[-1]
  milliseconds = milliseconds.replace(',', '')
  milliseconds = milliseconds.replace('.', '')
  milliseconds = int(milliseconds)

  if len(lap_time_parts) > 1:
    minutes = int(lap_time_parts[-2])
    milliseconds += 60 * 1000 * minutes

  lap_data.append(milliseconds)

##########################
# Cleanup the start time #
##########################

start_time_str = args.start_time.strip()
start_time_parts = start_time_str.split(':')

milliseconds = 1000 * int(start_time_parts[-1])

if len(start_time_parts) > 1:
  minutes = int(start_time_parts[-2])
  milliseconds += 60 * 1000 * minutes

if len(start_time_parts) > 2:
  hours = int(start_time_parts[-3])
  milliseconds += 60 * 60 * 1000 * hours

start_time = milliseconds

#########################################
# Create the Youtube description string #
#########################################

def lap_time_to_str(lap_time):
  hours = lap_time // (60 * 60 * 1000)
  minutes = (lap_time % (60 * 60 * 1000)) // (60 * 1000)
  seconds = (lap_time % (60 * 1000)) // 1000
  milliseconds = lap_time % 1000

  if hours != 0:
    return f"{hours}:{minutes:02}:{seconds:02}.{milliseconds:03}"

  if minutes != 0:
    return f"{minutes}:{seconds:02}.{milliseconds:03}"

  return f"{seconds:02}.{milliseconds:03}"

def time_to_timestamp(time):
  hours = time // (60 * 60 * 1000)
  minutes = (time % (60 * 60 * 1000)) // (60 * 1000)
  seconds = (time % (60 * 1000)) // 1000

  if hours != 0:
    return f"{hours}:{minutes:02}:{seconds:02}"

  return f"{minutes}:{seconds:02}"

timestamp_size = 10
lap_size = 5
sector_size = 12
lap_time_size = 12

youtube_description = "Lap times:\n"
youtube_description += f"{'Timestamp':>{timestamp_size}} "
youtube_description += f"{'Lap':>{lap_size}} "

if args.format == "default":

  youtube_description += f"{'Lap time':>{lap_time_size}}\n"

  best_lap_index = np.argmin(lap_data)
  best_lap = lap_data[best_lap_index]

  running_time = 0
  for lap_index, lap_time in enumerate(lap_data):

    video_time = start_time + running_time
    youtube_description += f"{time_to_timestamp(video_time):>{timestamp_size}} "
    youtube_description += f"{lap_index + 1:>{lap_size}} "

    lap_time_str = lap_time_to_str(lap_time)

    if lap_index == best_lap_index:
      lap_time_str = f"*{lap_time_str}*"
      youtube_description += "  "

    youtube_description += f"{lap_time_str:>{lap_time_size}}\n"
    running_time += lap_time

  youtube_description += "\n"

elif args.format in ("with_sectors", "wik"):

  for sector_index in range(3):
    header_name = f"Sector {sector_index + 1}"
    youtube_description += f"{header_name:>{sector_size}} "

  youtube_description += f"{'Lap time':>{lap_time_size}}\n"

  sector_data = []
  for sector_index in range(3):
    sector_data.append(lap_data[sector_index::4])

  lap_data = lap_data[3::4]

  best_sector_index = []
  best_sector = []
  for sector_index in range(3):
    best_sector_index.append(np.argmin(sector_data[sector_index]))
    best_sector.append(sector_data[sector_index][best_sector_index[sector_index]])

  best_lap_index = np.argmin(lap_data)
  best_lap = lap_data[best_lap_index]

  if args.format == "wik":
    # The first lap is not tracked
    youtube_description += f"{'-':>{timestamp_size}} "
    youtube_description += f"{1:>{lap_size}} "

    for _ in range(3):
      youtube_description += f"{'-':>{sector_size}} "

    youtube_description += f"{'-':>{lap_time_size}}\n"

  running_time = 0
  for lap_index, lap_time in enumerate(lap_data):

    lap_number = lap_index + 1
    if args.format == "wik":
      lap_number += 1

    video_time = start_time + running_time
    youtube_description += f"{time_to_timestamp(video_time):>{timestamp_size}} "
    youtube_description += f"{lap_number:>{lap_size}} "

    for sector_index in range(3):
      sector_time_str = lap_time_to_str(sector_data[sector_index][lap_index])

      if lap_index == best_sector_index[sector_index]:
        sector_time_str = f"*{sector_time_str}*"
        youtube_description += "  "

      youtube_description += f"{sector_time_str:>{sector_size}} "

    lap_time_str = lap_time_to_str(lap_time)

    if lap_index == best_lap_index:
      lap_time_str = f"*{lap_time_str}*"
      youtube_description += "  "

    youtube_description += f"{lap_time_str:>{lap_time_size}}\n"
    running_time += lap_time

  youtube_description += "\n"
  for sector_index in range(3):
    lap = best_sector_index[sector_index] + 1
    if args.format == "wik":
      lap += 1

    lap_time = lap_time_to_str(best_sector[sector_index])
    youtube_description += f"Best sector {sector_index + 1} at {lap}: {lap_time}\n"

youtube_description += f"Best lap at {best_lap_index + 1}: {lap_time_to_str(best_lap)}\n"

############################################
# print out the Youtube description string #
############################################
print("Here is the Youtube description:")
print()
print(youtube_description)
