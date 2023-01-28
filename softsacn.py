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

'''' Ideas
1) sacn has a receive ability - make a diagnostic target that, when enabled, overrides IPs
   for all or some universes, and instead sends it to the diagnostic target.  It would
   be a text window field of coloured blocks, corresponding to received data, with universes
   labelled.
2) 
'''


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


def senduniverse(su_universe, su_offset, su_channels, su_data):
    # su_universe - universe we are being asked to send
    # su_offset -
    #data - framebuffer
    # this function assumes we are supposed to send all channels for specified universe
    senduniversearr = arr.array('i', [])
    for i in range(su_offset, su_offset + su_channels):
        senduniversearr.append(su_data[i])
        sender[su_universe].dmx_data = senduniversearr
    #print("senduniverse = ", end=" ")
    #print(universe,end=" ")
    #prnstat("data: ", data, 0, "")
    #prnstat("senduniversearr: ", senduniversearr, 0, "")

    # This is what the SaCN library requires - a list of decimal values in channel
    # order to send to a specific [universe].  The next line is a quick PoC.
    # sender[33].dmx_data = (255,92,92, 255,92,92, 128,255,128, 128,255,128, 255,92,92, 128,255,128, 255,92,92, 255,128,128)  # 0-255 for each channel, starting from zero

    # By default, the SaCN library will resend its dmx_data once per second.
    # You can forcably update a universe at any time by calling sender[universe].


def inituniverses(uid):
    # uid - universe_initialization_dictionary
    offset = 0
    for un in list(uid):
        # un - current universe#; note - using a dictionary guarantees no duplicate keys
        # we need to iterate on a list(copy of dict), becuase we will remove any disabled
        #    universes during our iteration over the dict.
        if not(uid[un].get('disable')):  # universes enabled by default

            #initialize <argument> universe
            sender.activate_output(un)
            # note - multicast disables unicast; intentionally hardcoded to false for now
            sender[un].multicast = False
            # unicast target ip for <arg> universe
            sender[un].destination = uid[un]['ip']
            # create an index marking the start of this universe's channels in datarr
            uid[un]['offset'] = offset
            print("Done init of universe: " + str(un) +
                  " channel offset: " + str(offset), end=" ")
            # set "offset" to mark the end of this string, for use on the next string
            # note: arrays number from 0; thus the simple channel number yields the
            #       correct offset for the start of the next universe.
            offset = offset + uid[un]['channels']
            print("ip: " + uid[un]['ip'] + " next offset: " + str(offset))
        else:
            # best not to leave a disabled universe in the live list of universes!
            del(uid[un])
    # we return our dictionary, since we have modified it with offsets
    # "offset" just so happens to contain the total number of channels + 1.  We leave it like this
    # because range operators (eg: "for i in range(0,n)"") will stop at i=n-1
    return(uid, offset)


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
- pallets[]
-- pallets[0] Stephs 2022-12-24 antique look
-- pallets[1] Maximum R-G-B Pattern for bold testing
-- pallets[2] Cedric dining room chandelier antique look 2022-12-24

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

# Colour Pallettes
# defined in cfg['palettes'] - see configuration file

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
#universes, total_channels = inituniverses(universes)
universes, total_channels = init_universes(cfg)

# this is a static asumption of rbg lamps; safe for now.
# the plus 1 is becuase channels are zero based, so we need to add when counting
total_lamps = (total_channels) // 3
if total_channels % 3:
    print("Warning: " + str(total_channels) + " channels not divisible by 3")
else:
    print("Total Channels: "+str(total_channels) +
          " Total lamps: "+str(total_lamps))

for i in range(0, total_lamps):
    # Fill in random colours from colour pallette <n>:
    # this is by LAMP, since each colour selected will fill the next 3 channels
    # pick a colour (one of 3)

    # this would pick from a palette
    for j in range(0, 3):
        # whoops - need to settle on a base for colour numbers, eg: is hex c2022_antique_rgw
        color = cfg['palettes']['primary_colours'][j]['rgb']
        print("i = ", end=" ")
        print(i, end=" ")
        print("j = ", end=" ")
        print(j, end=" ")
        print("  color =", end=" ")
        print(color)
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

# time.sleep(10)  # send the data for 10 seconds

# I do not wish to call sender.stop, as it appears to send "blackout", and I
# prefer that the state of the lights latches.
# sender.stop()
print("")
print("Done.")
sys.exit()
