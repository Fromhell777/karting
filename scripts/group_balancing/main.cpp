#include "timer.hpp"
#include "prettyprint.hpp"

#include "group_shuffling.hpp"
#include "kart_info.hpp"

#include <cstddef>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>
#include <random>
#include <numeric>

double calculate_average_lap_time(t_Team const & team) {

  // The race effort is used as a weight for calculating the group average lap
  // time
  double sum = std::accumulate(team.cbegin(), team.cend(), 0.0,
                               [](double sum, t_Karter const & karter) {
                                 return karter.raceEffort / karter.averageLap + sum;});

  double normaliseFactor = std::accumulate(team.cbegin(), team.cend(), 0.0,
                                           [](double sum, t_Karter const & karter) {
                                           return karter.raceEffort + sum;});

  return normaliseFactor / sum;
}

double calculate_cost(t_Group const & group) {
  std::vector<double> teamAverageLaps;

  for (auto const & team : group) {
    teamAverageLaps.emplace_back(calculate_average_lap_time(team));
  }

  double const teamAverageLapSum = std::accumulate(teamAverageLaps.cbegin(),
                                                   teamAverageLaps.cend(), 0.0);
  double const meanTeamAverageLap = teamAverageLapSum / teamAverageLaps.size();

  double squareSum = 0.0;
  std::for_each(teamAverageLaps.cbegin(),
                teamAverageLaps.cend(),
                [&](double const teamAverageLap) {
                  squareSum += (teamAverageLap - meanTeamAverageLap) *
                               (teamAverageLap - meanTeamAverageLap);
                });

  double const stdDev = std::sqrt(squareSum / teamAverageLaps.size());

  return stdDev;
}

std::string groups_to_string(t_Groups const & groups) {

  std::string result = "";

  for (std::size_t g = 0; g < groups.size(); ++g) {

    if (g != 0) {result += ",\n";}

    result += '[';
    result += "\n  Group #" + std::to_string(g) + "\n";
    result += "  --------\n";

    for (std::size_t i = 0; i < groups[g].size(); ++i) {
      result += "\n  Team #" + std::to_string(i) + ":\n";
      result += "    Names: [";

      for (std::size_t j = 0; j < groups[g][i].size(); ++j) {
        result += groups[g][i][j].name;
        if (j + 1 != groups[g][i].size()) {result += ", ";}
      }

      result += "]\n    Avg lap time: ";
      result += std::to_string(calculate_average_lap_time(groups[g][i]));
      result += " ns";
    }

    result += "\n\n  Standard deviation: ";
    result += std::to_string(calculate_cost(groups[g]));

    result += "\n]";
  }

  return result;
}

bool perform_improvement(t_Group & group,
                         std::size_t const currentTeamIndex,
                         std::size_t const currentKarterIndex,
                         double & currentCost) {

  std::size_t const currentTeamSize = group[currentTeamIndex].size();

  for (std::size_t i = currentTeamIndex + 1; i < group.size(); ++i) {

    std::size_t const newTeamSize = group[i].size();

    // Check if the karters can be swapped
    if (std::find(group[currentTeamIndex][currentKarterIndex].unwantedTeamSizes.begin(),
                  group[currentTeamIndex][currentKarterIndex].unwantedTeamSizes.end(),
                  newTeamSize) !=
        group[currentTeamIndex][currentKarterIndex].unwantedTeamSizes.end()) {
      continue;
    }

    for (std::size_t j = 0; j < group[i].size(); ++j) {

      // Check if the karters can be swapped
      if (std::find(group[i][j].unwantedTeamSizes.begin(),
                    group[i][j].unwantedTeamSizes.end(),
                    currentTeamSize) !=
          group[i][j].unwantedTeamSizes.end()) {
        continue;
      }

      std::swap(group[currentTeamIndex][currentKarterIndex], group[i][j]);

      double const newCost = calculate_cost(group);

      if (newCost < currentCost) {
        currentCost = newCost;
        return true;
      } else {
        std::swap(group[currentTeamIndex][currentKarterIndex], group[i][j]);
      }

    }
  }

  return false;
}

t_Groups find_balanced_groups(t_GroupSizes const & groupSizes,
                              t_Karters const & karters) {

  auto groups = find_valid_configuration(groupSizes, karters);

  for (auto & group : groups) {

    // Minimize the cost function
    double currentCost = calculate_cost(group);

    for (std::size_t i = 0; i < group.size(); ++i) {
      for (std::size_t j = 0; j < group[i].size(); ++j) {

        while (perform_improvement(group, i, j, currentCost)) {}
      }
    }
  }

  return groups;
}

void check_group_sizes(t_GroupSizes const groupSizes, t_Karters const karters) {
  for (std::size_t i = 0; i < groupSizes.size(); ++i) {

    std::size_t const totalGroupSize = std::accumulate(groupSizes[i].cbegin(),
                                                       groupSizes[i].cend(), 0);

    std::size_t const  totalKarters = std::count_if(karters.cbegin(), karters.cend(),
                                                    [&](t_Karter const karter) {
                                                    return karter.groupNumber == i;});

    if (totalGroupSize != totalKarters) {
      std::string msg = "";
      msg += "ERROR: " + std::to_string(totalKarters);
      msg += " karters are in karting group " + std::to_string(i) + " while ";
      msg += std::to_string(totalGroupSize) + " karters are expected\n";
      throw std::invalid_argument(msg);
    }
  }
}

int main() {
  {
    timer Timer;

    std::uint32_t numIterations = 1000;

    auto karters = get_karters();
    auto const groupSizes = get_group_sizes();

    // Check if the requested group sizes match with the available karters
    check_group_sizes(groupSizes, karters);

    static std::random_device rd;
    static std::mt19937 gen(rd());

    t_Groups bestGroups;

    for (std::uint32_t i = 0; i < numIterations; ++i) {
      // Permute the starting order
      std::shuffle(karters.begin(), karters.end(), gen);

      auto const optimisedGroups = find_balanced_groups(groupSizes, karters);

      // Save the best results
      bool updatedGroups = false;
      if (i == 0) {
        bestGroups = optimisedGroups;
        updatedGroups = true;
      } else {
        for (std::size_t j = 0; j < optimisedGroups.size(); ++j) {
          if (calculate_cost(optimisedGroups[j]) < calculate_cost(bestGroups[j])) {
            bestGroups[j] = optimisedGroups[j];
            updatedGroups = true;
          }
        }
      }

      if (updatedGroups) {
        std::cout << "Best groups at iteration #" << i + 1 << ": "
                  << groups_to_string(bestGroups) << "\n\n";
      }
    }
  }
}
