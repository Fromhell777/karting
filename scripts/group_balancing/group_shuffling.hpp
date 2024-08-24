#pragma once

#include "kart_info.hpp"

#include <cstddef>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include <queue>
#include <algorithm>
#include <numeric>

bool breadth_first_search(
  std::vector<std::vector<std::size_t>> const & groupPositionToKarter,
  std::vector<std::size_t> const & matchesKarters,
  std::vector<std::size_t> const & matchesGroupPosition,
  std::vector<std::size_t> & distanceKarter) {

  std::queue<std::size_t> groupPositionQueue;

  for (std::size_t i = 0; i < matchesKarters.size(); ++i) {

    if (matchesKarters[i] == matchesGroupPosition.size()) {
      distanceKarter[i] = 0;
      groupPositionQueue.emplace(i);
    } else {
      distanceKarter[i] = matchesGroupPosition.size();
    }
  }

  while (not groupPositionQueue.empty()) {
    auto const groupPosition = groupPositionQueue.front();
    groupPositionQueue.pop();

    for (auto const karter : groupPositionToKarter[groupPosition]) {

      if (matchesGroupPosition[karter] == matchesKarters.size()) {
        return true;
      } else if (distanceKarter[matchesGroupPosition[karter]] ==
                 matchesGroupPosition.size()) {
        distanceKarter[matchesGroupPosition[karter]] = distanceKarter[groupPosition] + 1;
        groupPositionQueue.emplace(matchesGroupPosition[karter]);
      }

    }
  }

  return false;
}

bool depth_first_search(
  std::size_t const groupPosition,
  std::vector<std::vector<std::size_t>> const & groupPositionToKarter,
  std::vector<std::size_t> & matchesKarters,
  std::vector<std::size_t> & matchesGroupPosition,
  std::vector<std::size_t> & distanceKarter) {

  for (auto const karter : groupPositionToKarter[groupPosition]) {

    if (matchesGroupPosition[karter] == matchesKarters.size()) {

      matchesGroupPosition[karter] = groupPosition;
      matchesKarters[groupPosition] = karter;
      return true;

    } else if (distanceKarter[matchesGroupPosition[karter]] ==
               distanceKarter[groupPosition] + 1) {

      if (depth_first_search(matchesGroupPosition[karter],
                             groupPositionToKarter,
                             matchesKarters,
                             matchesGroupPosition,
                             distanceKarter)) {
        matchesGroupPosition[karter] = groupPosition;
        matchesKarters[groupPosition] = karter;
        return true;
      }

    }
  }

  distanceKarter[groupPosition] = matchesGroupPosition.size();
  return false;
}

t_Groups find_valid_configuration(t_GroupSizes const & groupSizes,
                                  t_Karters const & karters) {

  t_Groups groups(groupSizes.size());

  for (std::size_t g = 0; g < groupSizes.size(); ++g) {

    std::size_t const totalGroupSize = std::accumulate(groupSizes[g].cbegin(),
                                                       groupSizes[g].cend(), 0);

    // Extract the valid karters for this group
    t_Karters validKarters;
    for (auto const & karter: karters) {
      if (karter.groupNumber == g) {
        validKarters.emplace_back(karter);
      }
    }

    std::vector<std::vector<std::size_t>> groupPositionToKarter(totalGroupSize);

    std::size_t groupPositionIndex = 0;

    for (auto const teamSize : groupSizes[g]) {
      for (std::size_t k = 0; k < validKarters.size(); ++k) {

        if (std::find(validKarters[k].unwantedTeamSizes.begin(),
                      validKarters[k].unwantedTeamSizes.end(),
                      teamSize) ==
            validKarters[k].unwantedTeamSizes.end()) {

          for (std::size_t j = 0; j < teamSize; ++j) {
            groupPositionToKarter[groupPositionIndex + j].emplace_back(k);
          }

        }
      }

      // No karter wants this team size
      if (groupPositionToKarter[groupPositionIndex].empty()) {
        std::string msg = "";
        msg += "ERROR: No single karter allocation wants to be allocated in ";
        msg += "a team of size " + std::to_string(teamSize) + "for group ";
        msg += "number " + std::to_string(g) + '\n';
        throw std::invalid_argument(msg);
      }

      groupPositionIndex += teamSize;
    }

    // Perform the Hopcroft-Karp algorithm
    std::vector<std::size_t> matchesKarters(validKarters.size(),
                                            totalGroupSize);
    std::vector<std::size_t> matchesGroupPosition(totalGroupSize,
                                                  validKarters.size());

    std::size_t maximumCardinalityMatching = 0;

    std::vector<std::size_t> distanceKarter(validKarters.size());

    while (breadth_first_search(groupPositionToKarter, matchesKarters,
                                matchesGroupPosition, distanceKarter)) {

      for (std::size_t i = 0; i < validKarters.size(); ++i) {

        if (matchesKarters[i] == totalGroupSize) {
          if (depth_first_search(i, groupPositionToKarter, matchesKarters,
                                 matchesGroupPosition, distanceKarter)) {
            ++maximumCardinalityMatching;
          }
        }

      }
    }

    if (maximumCardinalityMatching != totalGroupSize) {
      std::string msg = "";
      msg += "ERROR: No valid starting karter allocation found based on the ";
      msg += "preferences for group number " + std::to_string(g) + '\n';
      throw std::invalid_argument(msg);
    }

    // Extract the resulting configuration into teams
    t_Group group(groupSizes[g].size());

    groupPositionIndex = 0;

    for (std::size_t i = 0; i < groupSizes[g].size(); ++i) {
      for (std::size_t j = 0; j < groupSizes[g][i]; ++j) {
        std::size_t const karterIndex = matchesKarters[groupPositionIndex + j];
        group[i].emplace_back(validKarters[karterIndex]);
      }

      groupPositionIndex += groupSizes[g][i];
    }

    groups[g] = group;
  }

  return groups;
}
