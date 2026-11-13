ldbd_names = {
    0: "dat",
    1: "tsmart",
    2: "doft",
    3: "chr",
    4: "tql",
    5: "tstop",
    6: "jbhunt",
}
local_temp_dir = {
    0: "data/01_raw/dat",
    1: "data/01_raw/tsmart",
    2: "data/01_raw/doft",
    3: "data/01_raw/chr",
    4: "data/01_raw/tql",
    5: "data/01_raw/tstop",
    6: "data/01_raw/jbhunt",
}
workers = {
    0: ["0", "1", "2", "3", "4", "5"],
    1: [""],
    2: ["0", "1", "2", "3", "4"],
    3: [""],
    4: [""],
    5: [""],
    6: [""],
}
prefix_s3 = {
    0: "DAT",
    1: "TSMARTER",
    2: "DOFT",
    3: "CHR",
    4: "TQL",
    5: "TSTOP",
    6: "JBHUNT",
}
paths_equips = {
    0: "data/01_raw/files/equips/dat_equips.csv",
    2: "data/01_raw/files/equips/doft_equips.csv",
    3: "data/01_raw/files/equips/chr_equips.csv",
    4: "data/01_raw/files/equips/tql_equips.csv",
    5: "data/01_raw/files/equips/tstop_equips.csv",
    6: "data/01_raw/files/equips/jbhunt_equips.csv",
}

ldbd_names_prod = {
    0: "dat",
    1: "trucksmarter",
    2: "doft",
    3: "chrobinson",
    4: "tql",
    5: "tstop",
    6: "jbhunt",
}

# Telegram
tokens_tlg = {
    0: "5917471051:AAExqZj2MqobX1rW3OZPYRvAG1TAM_Ssyfw",
    1: "5917471051:AAExqZj2MqobX1rW3OZPYRvAG1TAM_Ssyfw",
}
chats_id_tlg = ["1543457856", "6837868674", "6415038376", "6456401259", "670056024"]

output_folder = {
    0: "data/01_raw/dat",
    1: "data/01_raw/tsmart",
    2: "data/01_raw/doft",
    3: "data/01_raw/chr",
    4: "data/01_raw/tql",
    5: "data/01_raw/tstop",
    6: "data/01_raw/jbhunt",
}

paths_city_ldbd = {
    4: "data/01_raw/files/uscities_tql.csv",
    5: "data/01_raw/files/uscities_tstop.csv",
    6: "data/01_raw/files/uscities_jbhunt.csv",
}

loadboards_gs_aws = ["jbhunt", "tql"]
loadboards_os_aws = ['doft', 'dat', 'tsmart', "chr", "jbhunt", "tql", "tstop"]