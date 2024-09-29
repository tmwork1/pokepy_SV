import nxbt

nx = nxbt.Nxbt()
controller_index = nx.create_controller(nxbt.PRO_CONTROLLER)
nx.wait_for_connection(controller_index)
