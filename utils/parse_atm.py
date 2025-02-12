import pandas as pd 

ids = [381471, 263157, 780194]
rename_dict = {id: idx for idx, id in enumerate(ids)}

data = pd.read_csv('atm_data_train.csv')
description = pd.read_csv("df_places.csv")

part = data.loc[data['ATM_ID'].isin(ids)]
part = part.rename(columns={"Unnamed: 0": "Date"})
part = part.pivot_table(index='Date',values='Клиентский расход', columns=['ATM_ID'])
part = part.rename(columns=rename_dict)
part.to_csv("2025-spring/homeworks/hw1/data.csv")

columns = ('ATM_ID', 'ADDRESS', 'ADDR_ADDON', "LATITUDE","LONGITUDE")
part_description:pd.DataFrame  = description.loc[description['ATM_ID'].isin(ids)].loc[:, columns]
part_description = part_description.replace({'ATM_ID': rename_dict})
part_description.to_csv("2025-spring/homeworks/hw1/description.csv")
part_description