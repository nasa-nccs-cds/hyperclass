from hyperclass.data.aviris.manager import DataManager

c0 = (2000 ,2000)
c1 = (3000 ,3000)
file_name = "ang20170720t004130_corr_v2p9"

dm = DataManager()
dm.create_subtile(file_name,c0,c1)

