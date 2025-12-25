import argparse
import yaml
import xlsxwriter

#################
# Input parsing #
#################
parser = argparse.ArgumentParser(description = "Analyse the karting data.")

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
with open(args.input) as data_file:
  karting_data = yaml.safe_load(data_file)

###############
# Excel setup #
###############
# Create a workbook and add a worksheet
workbook = xlsxwriter.Workbook(args.output,
                               {"use_future_functions" : True})
worksheet = workbook.add_worksheet()

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
columns = len(karting_data["results"]) * 9 + 3
end_column_char = xlsxwriter.utility.xl_col_to_name(columns)
worksheet.set_column(f"A:{end_column_char}", 30)

# Sort the input data on position for consistency
karting_data["results"].sort(key = lambda team_data: team_data["finish_position"])

####################
# Helper functions #
####################
def count_drivers(karting_data):
  drivers = set()
  for team_data in karting_data["results"]:
    for lap in team_data["laps"]:
      drivers.add(lap["driver"])

  drivers.remove("Pit")

  return len(drivers)

def create_table(worksheet,
                 table_options,
                 begin_row,
                 end_row,
                 begin_column,
                 end_column,
                 header_format,
                 cell_format):

  for column in table_options["columns"]:
    column["format"] = cell_format

  begin_column_char = xlsxwriter.utility.xl_col_to_name(begin_column)
  end_column_char   = xlsxwriter.utility.xl_col_to_name(end_column)

  worksheet.add_table(f"{begin_column_char}{begin_row + 1}:{end_column_char}{end_row + 1}",
                      table_options)

  headers = [column["header"] for column in table_options["columns"]]
  for i, header in enumerate(headers):
    worksheet.write(begin_row,
                    begin_column + i,
                    header,
                    header_format)

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

team_table_name = "\"team\" & race_results[[#This Row],[Position]] & \"_results"

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
                               "formula" : f"=SUM(INDIRECT({team_table_name}[Lap times '[sec']]\")) / race_results[[#This Row],[Laps '[laps']]]"},
                              {"header"  : "Pit time [sec]",
                               "formula" : f"=SUMIF(INDIRECT({team_table_name}[Driver]\"), \"Pit\", INDIRECT({team_table_name}[Lap times '[sec']]\"))"},
                              {"header"  : "Pit stops",
                               "formula" : f"=COUNTIF(INDIRECT({team_table_name}[Driver]\"), \"Pit\")"},
                              {"header"  : "Average pit time [sec]",
                               "formula" : "=race_results[[#This Row],[Pit time '[sec']]] / race_results[[#This Row],[Pit stops]]"}]}

# Slowest lap formula
for i in range(len(total_data)):
  column_char = xlsxwriter.utility.xl_col_to_name(6)
  worksheet.write_formula(f"{column_char}{i + 3}",
                          f"{{=MAX(IF(INDIRECT({team_table_name}[Driver]\") <> \"Pit\", INDIRECT({team_table_name}[Lap times '[sec']]\")))}}")

create_table(worksheet     = worksheet,
             table_options = table_options,
             begin_row     = 1,
             end_row       = 1 + len(total_data),
             begin_column  = 0,
             end_column    = len(table_options["columns"]) - 1,
             header_format = header_format,
             cell_format   = cell_format)

end_column_char = xlsxwriter.utility.xl_col_to_name(len(table_options["columns"]) - 1)
worksheet.merge_range(f"A1:{end_column_char}1",
                      karting_data["race_name"],
                      merge_format)

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
                                 "formula" : f"=SUM(INDEX(team{i + 1}_results[Lap times '[sec']], 1):team{i + 1}_results[[#This Row], [Lap times '[sec']]])"},
                                {"header"  : "Distance to winner [laps]",
                                 "formula" : "=5"}]}

  begin_row     = len(karting_data["results"]) + count_drivers(karting_data) + 11
  begin_column  = i * (len(table_options["columns"]) + 1)
  end_column    = begin_column + len(table_options["columns"]) - 1

  create_table(worksheet     = worksheet,
               table_options = table_options,
               begin_row     = begin_row,
               end_row       = begin_row + len(lap_data),
               begin_column  = begin_column,
               end_column    = end_column,
               header_format = header_format,
               cell_format   = cell_format)

  begin_column_char = xlsxwriter.utility.xl_col_to_name(begin_column)
  end_column_char   = xlsxwriter.utility.xl_col_to_name(end_column)
  worksheet.merge_range(f"{begin_column_char}{begin_row}:{end_column_char}{begin_row}",
                        f"=INDEX(race_results[Team], MATCH({i + 1}, race_results[Position], 0))",
                        merge_format)

###########################
# Generate the Excel file #
###########################
workbook.close()


# TODO
# Scale all the cells with the correct width
# Add the charts
# Add the results table
# Add the driver table
# Add the interpolation data
