Automation for my chicken coop utilizing a raspberry pi controlling linear actuators for the doors, and relays for other items.  There are two versions:

without_web_interface:  Provides opening and closing of coop door and tunnel door based on sunrise and sunset times queried daily with astral.  

with_web_interface:  Same functionality as w/o but also includes Flask page that displays schedule data, temp, humidity, sunrise and dusk times.  There is a webcam feed from the coop as well as manual controls for all coop functions - open/close coop/tunnel, turn on/off IR light (for night camera) or coop light. - basically triggers relays.


