#pragma once

#include <cstddef>
#include <cstdint>
#include <iostream>
#include <vector>
#include <string>

struct t_Karter {
  std::string name;

  // Average lap time without outliers
  double averageLap;

  // Race effort. Must be between 1 and 0. It indicates how much time the karter
  // will drive. 1 meaning he will drive its fair part. 0 means the karter will
  // not drive at all
  double raceEffort;

  // Indicates which group the karter belongs to
  std::size_t groupNumber;

  // Indicates which team sizes they don't want to be part of
  std::vector<std::size_t> unwantedTeamSizes;

  friend std::ostream & operator<<(std::ostream & os, t_Karter const & karter);
};

std::ostream & operator<<(std::ostream & os, t_Karter const & karter) {
  os << karter.name;
  return os;
}

using t_Karters    = std::vector<t_Karter>;
using t_Team       = std::vector<t_Karter>;
using t_Group      = std::vector<t_Team>;
using t_Groups     = std::vector<t_Group>;
using t_GroupSizes = std::vector<std::vector<std::size_t>>;

t_Karters get_karters() {
  t_Karters karters;

  karters.emplace_back("Inigo",         34.502, 1.0, 0, std::initializer_list<std::size_t>{});
  karters.emplace_back("Kyle",          34.688, 1.0, 0, std::initializer_list<std::size_t>{});
  karters.emplace_back("BertP",         35.065, 1.0, 0, std::initializer_list<std::size_t>{});
  karters.emplace_back("RubenH",        35.163, 1.0, 0, std::initializer_list<std::size_t>{});
  karters.emplace_back("Sam",           35.251, 1.0, 0, std::initializer_list<std::size_t>{});
  karters.emplace_back("Yrjo",          35.404, 1.0, 0, std::initializer_list<std::size_t>{});
  karters.emplace_back("StefD",         35.372, 1.0, 0, std::initializer_list<std::size_t>{});
  karters.emplace_back("Jean-Philippe", 35.430, 1.0, 0, std::initializer_list<std::size_t>{});
  karters.emplace_back("Jonas",         35.404, 1.0, 0, std::initializer_list<std::size_t>{});
  karters.emplace_back("Steven",        35.477, 1.0, 0, std::initializer_list<std::size_t>{});
  karters.emplace_back("PieterR",       35.852, 1.0, 0, std::initializer_list<std::size_t>{});
  karters.emplace_back("Joost",         35.886, 1.0, 0, std::initializer_list<std::size_t>{});
  karters.emplace_back("Gert",          35.884, 1.0, 0, std::initializer_list<std::size_t>{});
  karters.emplace_back("Stefaan",       35.899, 1.0, 0, std::initializer_list<std::size_t>{});
  karters.emplace_back("Karel",         36.068, 1.0, 0, std::initializer_list<std::size_t>{});
  karters.emplace_back("Maarten",       36.169, 1.0, 0, std::initializer_list<std::size_t>{});
  karters.emplace_back("Willem",        36.112, 1.0, 0, std::initializer_list<std::size_t>{});
  karters.emplace_back("Stephanie",     36.423, 1.0, 0, std::initializer_list<std::size_t>{});
  karters.emplace_back("TimM",          36.387, 1.0, 0, std::initializer_list<std::size_t>{});
  karters.emplace_back("Mauro",         36.564, 0.7, 0, std::initializer_list<std::size_t>{});
  karters.emplace_back("Emil",          36.640, 1.0, 0, std::initializer_list<std::size_t>{});
  karters.emplace_back("StijnS",        37.720, 1.0, 0, std::initializer_list<std::size_t>{});
  karters.emplace_back("RubenD",        38.027, 1.0, 0, std::initializer_list<std::size_t>{});
  karters.emplace_back("BartG",         38.325, 0.4, 0, std::initializer_list<std::size_t>{});
  karters.emplace_back("StijnC",        38.729, 0.7, 0, std::initializer_list<std::size_t>{});

  return karters;
}

t_GroupSizes get_group_sizes() {

  t_GroupSizes groupSizes;

  groupSizes.emplace_back(std::initializer_list<std::size_t>{3, 3, 3, 3, 3,
                                                             3, 3, 2, 2});

  return groupSizes;
}
