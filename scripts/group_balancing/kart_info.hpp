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

  karters.emplace_back("Inigo",    36.160, 1.0, 1, std::initializer_list<std::size_t>{});
  karters.emplace_back("BertP",    36.881, 1.0, 1, std::initializer_list<std::size_t>{});
  karters.emplace_back("Kyle",     36.992, 1.0, 1, std::initializer_list<std::size_t>{});
  karters.emplace_back("Steven",   37.170, 1.0, 0, std::initializer_list<std::size_t>{2});
  karters.emplace_back("Joost",    37.600, 1.0, 1, std::initializer_list<std::size_t>{});
  karters.emplace_back("Ruben",    37.608, 1.0, 0, std::initializer_list<std::size_t>{2});
  karters.emplace_back("Matteo",   37.792, 1.0, 0, std::initializer_list<std::size_t>{2});
  karters.emplace_back("Pieter",   37.875, 1.0, 0, std::initializer_list<std::size_t>{2});
  karters.emplace_back("BertV",    37.934, 1.0, 0, std::initializer_list<std::size_t>{2});
  karters.emplace_back("Matt",     37.956, 1.0, 0, std::initializer_list<std::size_t>{2});
  karters.emplace_back("Mike",     38.025, 1.0, 0, std::initializer_list<std::size_t>{2});
  karters.emplace_back("Jasper",   38.025, 1.0, 1, std::initializer_list<std::size_t>{});
  karters.emplace_back("Tim",      38.036, 1.0, 1, std::initializer_list<std::size_t>{});
  karters.emplace_back("StefD",    38.096, 1.0, 0, std::initializer_list<std::size_t>{2});
  karters.emplace_back("Maarten",  38.346, 1.0, 0, std::initializer_list<std::size_t>{2});
  karters.emplace_back("Stefaan",  38.599, 0.9, 0, std::initializer_list<std::size_t>{2});
  karters.emplace_back("Finley",   39.001, 1.0, 0, std::initializer_list<std::size_t>{2});
  karters.emplace_back("Dario",    39.096, 1.0, 0, std::initializer_list<std::size_t>{2});
  karters.emplace_back("StefM",    39.262, 1.0, 0, std::initializer_list<std::size_t>{2});
  karters.emplace_back("Thomas",   39.409, 1.0, 0, std::initializer_list<std::size_t>{2});
  karters.emplace_back("Emil",     39.413, 1.0, 0, std::initializer_list<std::size_t>{2});
  karters.emplace_back("Jeff",     40.488, 1.0, 0, std::initializer_list<std::size_t>{2});
  karters.emplace_back("Stijn",    40.606, 1.0, 0, std::initializer_list<std::size_t>{2});
  karters.emplace_back("Toon",     41.719, 1.0, 0, std::initializer_list<std::size_t>{2});
  karters.emplace_back("Ilse",     41.905, 0.5, 0, std::initializer_list<std::size_t>{2});
  karters.emplace_back("Emiliano", 42.338, 0.6, 0, std::initializer_list<std::size_t>{2});
  karters.emplace_back("Bart",     44.704, 0.5, 0, std::initializer_list<std::size_t>{2});

  return karters;
}

t_GroupSizes get_group_sizes() {

  t_GroupSizes groupSizes;

  groupSizes.emplace_back(std::initializer_list<std::size_t>{3, 3, 3, 3,
                                                             3, 3, 3});
  groupSizes.emplace_back(std::initializer_list<std::size_t>{2, 2, 2});

  return groupSizes;
}
