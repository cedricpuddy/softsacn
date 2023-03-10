'''Libraries
- sacn: lowlevel E1.31/ArtNET data sender
- yaml: pyyaml for loading configuration data
- time, random, array: standard python libraries
'''
import sys
try:
    import sacn
    import time
    import random
    import array as arr
    import yaml
except ImportError:
    pass

config_file = "env/softsacn.yaml"

''' Functions
- prnstat():       gives a more readable version of the datarr "framebuffer" for low level debugging
- senduniverse():  sends the values for a given universe in datarr to the outside world
- inituniverses(): add universes/ips to sender object, and generate offsets
'''

def prnstat(prnname, prnarr, k, l):
    print("")
    print(prnname, end=" ")
    for m in prnarr:
        print(str(m).zfill(3), end=',')
    print("  k =", end=" ")
    print(k, end=l)


def senduniverse(su_universe):
    # The SaCN library requires a list of decimal values in channel
    # order to send to a specific [universe].  The next line is a quick PoC.
    # sender[33].dmx_data = (255,92,92, 255,92,92, 128,255,128, 128,255,128, 255,92,92, 128,255,128, 255,92,92, 255,128,128)  # 0-255 for each channel, starting from zero

    # This function uses the universe offset vaule to slice the required
    # channels out of the dataarr.  This function is for readability, not
    # because it encapsulates any complex functionality.

    # We just use the structure directly; we could easily add an argument
    # and pass in a copy, if required at some point.

    i_offset = universes[i_unv]['offset']
    sender[i_unv].dmx_data = datarr[i_offset:i_offset +
                                    universes[i_unv]['channels']]

# load config file
# returns a dictionary of universes, or None if error

def load_config(config_file):
    try:
        with open(config_file, 'r') as ymlfile:
            cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)
    except FileNotFoundError:
        print(f"Error: {config_file} not found.")
        return
    except yaml.YAMLError as e:
        print(f"Error: {e}")
        return
    # Sanity check for universes key
    if 'universes' not in cfg:
        print("Error: 'universes' key not found in config file.")
        return
    return cfg

# init_universes() - initialize universes
# returns a dictionary of universes, or None if error

def init_universes(cfg):
    offset = 0
    for un in cfg['universes']:
        if not(cfg['universes'][un].get('disable')):  # universes enabled by default
            sender.activate_output(un)
            sender[un].multicast = False
            sender[un].destination = cfg['universes'][un]['ip']
            cfg['universes'][un]['offset'] = offset
            print("Done init of universe: " + str(un) +
                  " channel offset: " + str(offset), end=" ")
            offset = offset + cfg['universes'][un]['channels']
            print("ip: " + cfg['universes'][un]
                  ['ip'] + " next offset: " + str(offset))
        else:
            # best not to leave a disabled universe in the live list of universes!
            del(cfg['universes'][un])
    return(cfg['universes'], offset)

def marquie(universe,seqs,cfg):
    # universe # to render
    # seqs - name of the sequence to be used
    # cfg copy of the cfg array
    print ("Marquie running - universe: " + str(universe) + " seqs: " + seqs)

'''
seqs:
    sequence: "main"
        universes: "33"
        palette: "w2023_mardiegras"
        effect: "marquie"
            - nodes: "gold,purple,purple,gold,green,green"
cfg['effectfunctions']=('marquie')
'''
def init_seqs(cfg):
    for seqs in cfg['seqs']:
        if not(cfg['seqs'][seqs].get('disable')):  # seqs enabled by default
            if not(cfg['seqs'][seqs].get('universes')): #if no universes are stipulated, apply to *all* universes
                is_universes=cfg['universes']
            else:
                is_universes=cfg['seqs'][seqs]['universes']
            # if not(cfg['effectfunctions']) -- will filter effect functions later
            for i in is_universes:
                marquie(i,seqs,cfg)
        else:
            # best not to leave a disabled universe in the live list of universes!
            del(cfg['seqs'][seqs])        


# color_lookup[] - array of colors for each LED
color_lookup = {}

# fill_color_lookup() - fill the color_lookup[] array with random colors
#   numberOfLeds - number of LEDs in the array
#   color_range - tuple of min/max values for each color (default: 240-255)
# returns color_lookup[]

def fill_color_lookup(numberOfLeds, color_range=(240, 255)):
    color_lookup.clear()
    for i in range(numberOfLeds):
        color_lookup[i] = (random.randint(color_range[0], color_range[1]),
                           random.randint(color_range[0], color_range[1]),
                           random.randint(color_range[0], color_range[1]))
        print("color_lookup[" + str(i) + "] = " + str(color_lookup[i]))
    return color_lookup

'''
Data Structures

- universes{} is a list of "universes", each of which addresses up to 510
  "channels" (thus 170 RGB lights), by IP address.  The universe number needs
  to be unique, and needs to be configured on the receiving E1.31/ArtNET/DMX
  "controller".
  
  Channels: we currently assume our channels to be arranged as RGB triples 
    for each given "lamp".  We use the # of channels to compute the number
    of lamps, so that we can write code in terms of either lamps or channels.
  Lamp: a single discrete logical light in a string/fixture/etc.  For our purposes, we
    will often/usually be setting a specific colour by RGB value to a given light, but
    hope to have logic that can apply colour temperature/gamma tweaks to specific sets
    of lamps (eg: all the lights down low look dimmer than the lights up high due to
    directionality of LEDs, so strategically dimming values on certain strings would
    result in them visually matching; or for accomodating lights from different vendors
    that have different Colour Rendering Indexes (CRI)).
  Controller: assumed to be a mostly dumb E1.31 receiving gateway that knows how to turn 
    lists of (channel#,intensity#) data into actual light.

  List of Universes - stored in nested dictionaries:
    - Now loaded from a YAML config file in to cfg['universes'] dictionary.
    - Each universe # is a key, the associated value is a dictionary of settings.
    - assume channels are rgb, unless specified otherwise; eventually there will be
      logic to deal with alternate channel maps  ('"type": "brg"', or similar)
    - To Disable a Universe: add '"disable":1,' to the universe definition.
  
    Example dictionary: 
      universes = {
      1: {"disable": 0, "ip": "10.0.0.10", "channels": 150,
        "hostname": "D191-DR-Tree1", "desc": "Tree on D191 Controller"}}
    "Hostname" and "desc" are free form fields at the moment.

- datarr[] - our current state of the lights (think "framebuffer")
- holdrr[] - array to for caching temporary copies of state; ultimately expected
             to become part of a effect function.  Eg: to flash a light, we
             we pop the original colours on there, then restore those original 
             colours to end the flash.
'''

# Colour Pallettes -- defined in cfg['palettes'] - see configuration file

# create our blank framebuffers
datarr = arr.array('i', [])
holdrr = arr.array('i', [])

'''
Main Section
- calls to initialize the sACN sender object and universes
- calling init universes calculates offsets into a blank datarr array
- datarr[] contains all channels (like a framebuffer).  The start of each
  set of channels is in the offset key in universes{}
'''
# See if we have a configuration, and load it
cfg = load_config(config_file)
print ("softsacn: Configuration Loaded")

# Initialize the ArtNET/DMX/E1.31 senders
sender = sacn.sACNsender()  # initialize object
# start the sending thread
sender.start()
print ("softsacn: Sender thread started")

# send our univ. list, get it back with offsets & total number of channels
universes, total_channels = init_universes(cfg)

# this is a static asumption of rbg lamps; safe for now.
# the plus 1 is becuase channels are zero based, so we need to add when counting
total_lamps = (total_channels) // 3
if total_channels % 3:
    print("Warning: " + str(total_channels) + " channels not divisible by 3")
else:
    print("Total Channels: "+str(total_channels) +
          " Total lamps: "+str(total_lamps))


i=0
#print(cfg)
while i < total_lamps+2:
    for j in cfg['seqs']['main']['nodes']:
        cur_palette=cfg['seqs']['main']['palette']
        #print ("j= "+str(j)+ "cur_palette= "+cur_palette)
        #print (cfg['palettes'][cur_palette][int(j)])
        color = (cfg['palettes'][cur_palette][int(j)]['rgb'])
        (r, g, b) = color.split(',')
        datarr.append(int(r))
        datarr.append(int(g))
        datarr.append(int(b))

        # print("lamp= " + str(i) + " palette_col= " + str(j) + " color= " + color, end=" " )
    i = i+1


'''
for i in range(0, total_lamps):
    # Fill in random colours from colour pallette <n>:
    # this is by LAMP, since each colour selected will fill the next 3 channels
    # pick a colour (one of 3)

    for j in cfg['seqs']['main']['nodes']:
        color = (cfg['palettes']['w2023_mardiegras'][j]['rgb'])

        # whoops - need to settle on a base for colour numbers, eg: is hex c2022_antique_rgw
        color = cfg['palettes']['w2023_mardiegras'][j]['rgb']
        print("i= " + str(i) + " j= " + str(j) + " color= " + color )
        (r, g, b) = color.split(',')
        datarr.append(int(r))
        datarr.append(int(g))
        datarr.append(int(b))

    # for this pattern, we want it based on blue, so lets pick a random blue...
    blue = random.randint(75, 250)
    for i_rgb in range(0, 3):
        # and then randomly set our r,g colours basedo on the blue
        # intensity=random.randint(blue-60,blue)
        if (i_rgb == 0):
            datarr.append(random.randint(blue//5, blue//3))
        if (i_rgb == 1):
            datarr.append(random.randint(blue//3, blue))
        if (i_rgb == 2):
            datarr.append(blue)
    '''        
print("init data filled")
prnstat("datarr: ", datarr, 0, "")
print("")

print("Sending universe(s): ", end="")
# while total_channels:
for i_unv in universes:
    i_offset = universes[i_unv]['offset']
    # we pick a slice of the datarr buffer that maps to a given universe, and
    # hand it to the sender instance for that universe, and tada, let there be light.
    sender[i_unv].dmx_data = datarr[i_offset:i_offset +
                                    universes[i_unv]['channels']]
    print(i_unv, end=" ")
    # time.sleep(5)


#prnstat("datarr: ", datarr, 0,"")
#prnstat("holdrr: ", holdrr, 0,"\n")

count = 0

# this is a basic "twinkle" effect, but it uses a lookup table to
# generate the random colours.  This is a bit faster than the above
# method
# change to "while True" to enable.

'''
fill_color_lookup(total_lamps, (240, 255))
while True:
    # note, this code is functionally broken, middle of being reworked
    # but it does roughly illustrate temporarily changing a selection of lights
    # the colours of some lights -- pick some channels, pick some colours
    # save the origial colours, change the colours, send the array,
    # wait, and then change it back.
    k = random.randint(0, 63)
    k = k*3
    for i in range(k, k+3):
        r, g, b = color_lookup[i]
        holdrr.append(datarr[i])
        datarr[i] = r
        datarr[i+1] = g
        datarr[i+2] = b
    print(f"LED {k/3+1} RGB values: {r}, {g}, {b}")
    #senduniverse(33, 0, 42, datarr)
    #senduniverse(1, 43, 192, datarr)
    i_inv = 0
    i_offset = universes[i_unv]['offset']
    sender[i_unv].dmx_data = datarr[i_offset:i_offset +
                                    universes[i_unv]['channels']]
    for i in range(0, 3):
        datarr[k+i] = holdrr.pop(0)
    holdrr = arr.array('i', [])
    count += 1
'''



# I do not wish to call sender.stop, as it appears to send "blackout", and I
# prefer that the state of the lights latches.
# sender.stop()
print("")
print("Done.")
sys.exit()
