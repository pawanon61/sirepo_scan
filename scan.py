import datetime
from detector import LclsDetector
from ophyd.sim import SynAxis
from ophyd import Device, Component as Cpt
import bluesky.plans as bp
from bluesky import RunEngine
from bluesky.callbacks.best_effort import BestEffortCallback
from databroker import Broker
import matplotlib.pyplot as plt
plt.switch_backend('agg') #so that matplotlib doesnot look for display environment
import os
import argparse
import h5py

def get_args():
	parser = argparse.ArgumentParser()
	parser.add_argument('-xi', '--x_initial', type = int, help = 'starting x axis value', required = True)
	parser.add_argument('-xf', '--x_final', type = int, help = 'final x axis value', required = True)
	parser.add_argument('-xs', '--x_steps', type = int, help = 'number of steps in x axis', required = True)
	parser.add_argument('-yi', '--y_initial', type = int, help = 'starting y axis value', required = True)
	parser.add_argument('-yf', '--y_final', type = int, help = 'final y axis value', required = True)
	parser.add_argument('-ys', '--y_steps', type = int, help = 'number of steps in y axis', required = True)
	parser.add_argument('-id', '--simid', type = str, help = 'simulation id, 8 digit from address in browser', required = True)
	args = parser.parse_args()
	xi_arg = args.x_initial
	xf_arg = args.x_final
	xs_arg = args.x_steps
	yi_arg = args.y_initial
	yf_arg = args.y_final
	ys_arg = args.y_steps
	id_arg = args.simid
	return xi_arg, xf_arg, xs_arg, yi_arg, yf_arg, ys_arg, id_arg
xi, xf, x_steps, yi, yf, y_steps, sim_id = get_args()

uid = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
data_dir = os.path.abspath('.') + '/data' 
if not os.path.exists(data_dir):
	os.makedirs(data_dir)
image_dir = os.path.abspath('.') + '/images' 
if not os.path.exists(image_dir):
	os.makedirs(image_dir)
# to store images from each step of scan
hf5_file = data_dir + "/%s_images.h5" %uid
hf5 = h5py.File(hf5_file, 'w')
hf5.close()

RE = RunEngine({})
# prepare live visualization
bec = BestEffortCallback()
# Send all metadata/data captured to the BestEffortCallback.
RE.subscribe(bec)
# temporary sqlite backend
db = Broker.named('temp')
# Insert all metadata/data captured into db.
RE.subscribe(db.insert)

class Slit(Device):
	xmotor = Cpt(SynAxis)
	ymotor = Cpt(SynAxis)
# import pdb; pdb.set_trace()
slit = Slit(name = 'slit')
# hence, the name of motors will be slit_xmotor and slit_ymotor respectively

detector = LclsDetector('slitdetector', slit.xmotor, 'slit_xmotor', slit.ymotor, 'slit_ymotor', sim_id, image_file = hf5_file)
detector.read_attrs = ['maxim']  # name of component for read()

# center position of mirror goes from 0 to 1 mm on both axes
RE(bp.grid_scan([detector], slit.xmotor, xi, xf, x_steps, slit.ymotor, yi, yf, y_steps, False))

plt.savefig(image_dir + '/%s_maxIntensity.png' %uid)
plt.clf()

# plot scan intensities at different steps (by reading info from hdf5 file where they were stored during the scan)
hf5 = h5py.File(hf5_file, 'r')
keys = [key for key in hf5.keys()]
# plot
# plt.rcParams['xtick.top'] = plt.rcParams['xtick.labeltop'] = True
fig, ax = plt.subplots(nrows = y_steps, ncols = x_steps)
c = 0
for i, row in enumerate(reversed(ax)):
	for j, col in enumerate(row):
		col.imshow(hf5[keys[c]], aspect = 'auto', origin = 'lower')
		if not (i==0 and j==0):
			col.tick_params(labelleft = False, labelbottom = False)
		else:
			pass
		c += 1
fig.suptitle("x range: %s  &  y range: %s \nscan starts from bottom left" %(hf5['x_range'][:], hf5['y_range'][:]), fontsize = 8)
fig.subplots_adjust(top = 0.88, wspace=0.01, hspace=0.01)
plt.savefig(image_dir + '/%s_beamLocation.png' %uid)
hf5.close()
