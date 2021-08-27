# P5GEMOfflineMonitor
Tool that queries the DCS database and generates a rootfile containing V_mon and I_mon plots per electrode/chamber.
Originally developed by `simonepv` (see: https://github.com/simonepv/P5GEMOfflineMonitor).
Minor changes to integrate it with GEM efficiency code
------

## Installation
1. Clone from github
```bash
cd your_working_directory
git clone git@github.com:gem-dpg-pfa/P5GEMOfflineMonitor.git
```
2. Setup environmental variables
Sensitive database information must be added to the script setup_DCS.sh. Please contact the developers.
```bash
cd P5GEMOfflineMonitor
source setup_DCS.sh
```
## How to execute
1. Prepare list of chambers of interest by modifying `P5GEMChosenChambers_HV.txt` or `P5GEMChosenChambers_LV.txt`. In case you need DCS trends for all chambers, ignore this step.
2. Run the script, limiting the output to the list of `ChosenChambers`:
```bash
python GEMDCSP5Monitor.py 2021-04-01_15:22:31 2021-04-02_15:22:31 HV 0
```
   Add `-all` flag to include all 72 chambers.
