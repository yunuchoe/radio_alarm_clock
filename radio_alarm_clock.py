from machine import Pin, SPI, I2C # SPI is a class associated with the machine library. 
import machine
import utime

# The below specified libraries have to be included. Also, ssd1306.py must be saved on the Pico. 
from ssd1306 import SSD1306_SPI # this is the driver library and the corresponding class
import framebuf # this is another library for the display. 
    
# Define columns and rows of the oled display. These numbers are the standard values. 
SCREEN_WIDTH = 128 #number of columns
SCREEN_HEIGHT = 64 #number of rows

# Initialize I/O pins associated with the oled display SPI interface

spi_sck = Pin(18) # sck stands for serial clock; always be connected to SPI SCK pin of the Pico
spi_sda = Pin(19) # sda stands for serial data;  always be connected to SPI TX pin of the Pico; this is the MOSI
spi_res = Pin(21) # res stands for reset; to be connected to a free GPIO pin
spi_dc  = Pin(20) # dc stands for data/command; to be connected to a free GPIO pin
spi_cs  = Pin(17) # chip select; to be connected to the SPI chip select of the Pico 

#
# SPI Device ID can be 0 or 1. It must match the wiring. 
#
SPI_DEVICE = 0 # Because the peripheral is connected to SPI 0 hardware lines of the Pico

#
# initialize the SPI interface for the OLED display
#
oled_spi = SPI( SPI_DEVICE, baudrate= 100000, sck= spi_sck, mosi= spi_sda )

#
# Initialize the display
#
oled = SSD1306_SPI( SCREEN_WIDTH, SCREEN_HEIGHT, oled_spi, spi_dc, spi_res, spi_cs, True )

radio_frequency = 107.3
radio_volume = 0
mute_status = True

#From ECE 299 Lab 3 (class Radio)         
class Radio:
    
    def __init__( self, NewFrequency, NewVolume, NewMute ):
#
# set the initial values of the radio
#
        self.Volume = radio_volume
        self.Frequency = radio_frequency
        self.Mute = mute_status
#
# Update the values with the ones passed in the initialization code
#
        self.SetVolume( NewVolume )
        self.SetFrequency( NewFrequency )
        self.SetMute( NewMute )    
      
# Initialize I/O pins associated with the radio's I2C interface

        self.i2c_sda = Pin(26)
        self.i2c_scl = Pin(27)
#
# I2C Device ID can be 0 or 1. It must match the wiring. 
#
# The radio is connected to device number 1 of the I2C device
#
        self.i2c_device = 1 
        self.i2c_device_address = 0x10
#
# Array used to configure the radio
#
        self.Settings = bytearray( 8 )
        self.radio_i2c = I2C( self.i2c_device, scl=self.i2c_scl, sda=self.i2c_sda, freq=200000)
        self.ProgramRadio()

    def SetVolume( self, NewVolume ):
#
# Convert the string into a integer
#
        try:
            NewVolume = int( NewVolume )   
        except:
            return( False )
#
# Validate the type and range check the volume
#
        if ( not isinstance( NewVolume, int )):
            return( False )
        
        if (( NewVolume < 0 ) or ( NewVolume >= 16 )):
            return( False )

        self.Volume = NewVolume
        return( True )

    def SetFrequency( self, NewFrequency ):
#
# Convert the string into a floating point value
#
        try:
            NewFrequency = float( NewFrequency )  
        except:
            return( False )
#
# validate the type and range check the frequency
#
        if ( not ( isinstance( NewFrequency, float ))):
            return( False )
        if (( NewFrequency < 88.0 ) or ( NewFrequency > 108.0 )):
            return( False )
        self.Frequency = NewFrequency
        return True
        
    def SetMute( self, NewMute ):
        try:
            self.Mute = bool( int( NewMute ))  
        except:
            return( False )
        
        return( True )
#
# convert the frequency to 10 bit value for the radio chip
#
    def ComputeChannelSetting( self, Frequency ):
        Frequency = int( Frequency * 10 ) - 870
        ByteCode = bytearray( 2 )
#
# split the 10 bits into 2 bytes
#
        ByteCode[0] = ( Frequency >> 2 ) & 0xFF
        ByteCode[1] = (( Frequency & 0x03 ) << 6 ) & 0xC0
        return( ByteCode )
#
# Configure the settings array with the mute, frequency and volume settings
#
        if ( self.Mute ):
            self.Settings[0] = 0x80
        else:
            self.Settings[0] = 0xC0
        self.Settings[1] = 0x09 | 0x04
        self.Settings[2:3] = self.ComputeChannelSetting( self.Frequency )
        self.Settings[3] = self.Settings[3] | 0x10
        self.Settings[4] = 0x04
        self.Settings[5] = 0x00
        self.Settings[6] = 0x84
        self.Settings[7] = 0x80 + self.Volume
#        
# Update the settings array and transmit it to the radio
#
    def ProgramRadio( self ):        
        try:
            self.UpdateSettings()
            self.radio_i2c.writeto(self.i2c_device_address, self.Settings)
        except OSError as e:
            print("Error")
            self.ProgramRadio()

#
# Extract the settings from the radio registers
#
    def GetSettings( self ):
#        
# Need to read the entire register space. This is allow access to the mute and volume settings
# After and address of 255 the 
#
        self.RadioStatus = self.radio_i2c.readfrom( self.i2c_device_address, 256 )

        if (( self.RadioStatus[0xF0] & 0x40 ) != 0x00 ):
            MuteStatus = False
        else:
            MuteStatus = True
            
        VolumeStatus = self.RadioStatus[0xF7] & 0x0F
 
 #
 # Convert the frequency 10 bit count into actual frequency in Mhz
 #
        FrequencyStatus = (( self.RadioStatus[0x00] & 0x03 ) << 8 ) | ( self.RadioStatus[0x01] & 0xFF )
        FrequencyStatus = ( FrequencyStatus * 0.1 ) + 87.0
        
        if (( self.RadioStatus[0x00] & 0x04 ) != 0x00 ):
            StereoStatus = True
        else:
            StereoStatus = False
        
        return( MuteStatus, VolumeStatus, FrequencyStatus, StereoStatus )

# Our variables
hour = 11
minute = 22 # 
second = 50
period = 'AM'  # set to 'AM' or 'PM'

format = 12 # set to 12 or 24

increment = 1 # factor for our plus/minus in time and alarm states
increment_pointer = 0 # rolling pointer for below array
incremenet_list = [1, 2, 5, 10, 30] # possible values that can be assigned to increment

alarm_set = False # alarm starts off
alarm_hour = hour 
alarm_minute = minute
alarm_period = period
snooze_minute = 5 # default snooze time (configurable)


#
# initialize the FM radio (Also from ECE 299 Lab 3)
#
fm_radio = Radio( radio_frequency, radio_volume, mute_status )

state = 0
# 0 = default (shows clock - change volume/radio freq)
# 1 = format (pick 12 or 24 hours)
# 2 = time (change hour, minute and (pm/am))
# 3 = alarm (add, remove or edit alarm)
# 4 = radio (station, sound, mute)

# Assign inputs and switches

button_1 = machine.Pin(2, machine.Pin.IN, machine.Pin.PULL_UP) # leftmost button
button_2 = machine.Pin(3, machine.Pin.IN, machine.Pin.PULL_UP)
button_3 = machine.Pin(4, machine.Pin.IN, machine.Pin.PULL_UP)
button_4 = machine.Pin(5, machine.Pin.IN, machine.Pin.PULL_UP) # rightmost button

switch = machine.Pin(15, machine.Pin.IN, machine.Pin.PULL_DOWN)

button_1_pressed = False # default state for button is unpressed
button_2_pressed = False
button_3_pressed = False
button_4_pressed = False

# Common functions

def change_format(): # changes hours if format is changed
    global format
    global period
    global hour
    if	format == 12:
        format = 24
        if period == 'PM':
            hour += 12
    else:
        format = 12
        if hour > 12:
            hour -=12
    print(format)

def alarm_set_notification(): # top right indicator for alarm being set
    global alarm_set
    if alarm_set == False:
        oled.text("( )", 104, 0);
    else:
        oled.text("(A)", 104, 0);
        
def increment_function(): # how our increment function works
    global increment
    global increment_pointer
    increment_pointer+=1
    increment = incremenet_list[increment_pointer % 5]
            

def button_1_handler(pin): # functions of button 1
    global button_1_pressed
    global state
    global acounter
    global alarm_set
    global radio_volume
    global mute_status
    if not button_1_pressed:
        print("Button 1")
        button_1_pressed = True
        
        if state == 0: # main menu
            state = 1
        
        elif state == 1: # time format - Back
            state = 0
            
        elif state == 2: # change time - Back
            state = 0
            
        elif state == 3: # alarm - Back
            state = 0
            
        elif state == 32: # alarm - Add/Edit
            state = 0
            alarm_set = True
            
        elif state == 33: # alarm - Snooze
            state = 3
            
        elif state == 4: # radio - Back
            state = 0
        
        elif state == 42: # radio - Station
            state = 4
        
        elif state == 43: # radio - Vol
            state = 4
        elif state == 5: # alarm - accept
            radio_volume = 0
            if ( fm_radio.SetVolume( radio_volume ) == True ):
                fm_radio.ProgramRadio()
            mute_status = True
            if ( fm_radio.SetMute( mute_status ) == True ):
                fm_radio.ProgramRadio()
            alarm_set = False
            state = 0
        
            
def button_2_handler(pin): # functions of button 2
    global button_2_pressed
    global state
    global format
    global hour
    global period
    global radio_frequency
    global radio_volume
    global mute_status
    global snooze_minute
    global alarm_hour
    global alarm_period
    global alarm_minute
    global snooze_minute
    if not button_2_pressed:
        print("Button 2")
        button_2_pressed = True
                
        if state == 0: # main menu
            state = 2
        
        elif state == 1: # time format - change to 24 to 12 hour format
            if format == 24:
                format = 12
                if hour > 12:
                    period = 'PM'
                    hour -=12
                else:
                    period = 'AM'
                    
                if alarm_hour > 12:
                    alarm_period = 'PM'
                    alarm_hour -= 12
                else:
                    alarm_period = 'AM'
                    
                if hour == 0:
                    hour = 12
                if alarm_hour == 0:
                    alarm_hour = 12
            state = 0
            
        elif state == 2: # change time
            if format == 24:
                if switch.value() == False:
                    hour = (hour + 1*increment) % 24
                elif switch.value() == True:
                    hour = (hour - 1*increment) % 24
            else:
                if	switch.value() == False:  # Increase time
                    previous_hour = hour
                    hour = (hour + 1*increment)

                    if	previous_hour < 12 and hour >= 12:
                        if	period == 'AM':
                            period = 'PM'
                        else:
                            period = 'AM'
                    if	hour > 12:
                        hour -= 12
                elif	switch.value() == True:  # Decrease time
                    previous_hour = hour
                    hour = (hour - 1*increment)

                    if	(previous_hour > 1 and hour <= 0) or (previous_hour >= 12 and hour <= 11):
                        if	period == 'AM':
                            period = 'PM'
                        else:
                            period = 'AM'
                    if	hour < 1:
                        hour += 12
                
        elif state == 3: # alarm
            state = 32
            
        elif state == 32: # alarm
            if format == 24:
                if switch.value() == False:
                    alarm_hour = (alarm_hour + 1*increment) % 24
                elif switch.value() == True:
                    alarm_hour = (alarm_hour - 1*increment) % 24
            else:
                if	switch.value() == False:  # Increase time
                    previous_alarm_hour = alarm_hour
                    alarm_hour = (alarm_hour + 1*increment)

                    if	previous_alarm_hour < 12 and alarm_hour >= 12:
                        if	alarm_period == 'AM':
                            alarm_period = 'PM'
                        else:
                            alarm_period = 'AM'
                    if	alarm_hour > 12:
                        alarm_hour -= 12
                elif	switch.value() == True:  # Decrease time
                    previous_alarm_hour = alarm_hour
                    alarm_hour = (alarm_hour - 1*increment)

                    if	(previous_alarm_hour > 1 and alarm_hour <= 0) \
                       or (previous_alarm_hour >= 12 and alarm_hour <= 11):
                        if	alarm_period == 'AM':
                            alarm_period = 'PM'
                        else:
                            alarm_period = 'AM'
                    if	alarm_hour < 1:
                        alarm_hour += 12
                
        elif state == 33: # alarm
            snooze_minute = (snooze_minute + (1*increment))
            if snooze_minute > 60:
                snooze_minute -=60
            
        elif state == 4: # radio
            state = 42
        
        elif state == 42: # increase radio frequency
            radio_frequency = radio_frequency + (0.1*increment)

            if ( fm_radio.SetFrequency( radio_frequency ) == True ):
                fm_radio.ProgramRadio()
                
        elif state == 43: # increase radio volume
            radio_volume = (radio_volume + (1*increment)) % 16

            if ( fm_radio.SetVolume( radio_volume ) == True ):
                fm_radio.ProgramRadio()
                
        elif state == 5: # alarm - snooze
            radio_volume = 0
            if ( fm_radio.SetVolume( radio_volume ) == True ):
                fm_radio.ProgramRadio()
            mute_status = True
            if ( fm_radio.SetMute( mute_status ) == True ):
                fm_radio.ProgramRadio()
            alarm_minute += snooze_minute
            if alarm_minute > 59:
                alarm_hour += 1
                alarm_minute -= 60
            state = 0

def button_3_handler(pin): # functions of button 3
    global button_3_pressed
    global state
    global format
    global hour
    global minute
    global radio_frequency
    global radio_volume
    global snooze_minute
    global alarm_minute
    if not button_3_pressed:
        print("Button 3")
        button_3_pressed = True
        
        if state == 0: # main menu
            state = 3
        
        elif state == 1: # time format - change to from 12 to 24 hour format
            if format == 12:
                format = 24
                if period == 'PM':
                    hour += 12
            state = 0
            
        elif state == 2: # change time
            if switch.value() == False:
                minute = (minute + 1*increment) % 60
            elif switch.value() == True:
                minute = (minute - 1*increment) % 60
            
        elif state == 3: # alarm
            state = 33
            
        elif state == 32: # alarm
            if switch.value() == False:
                alarm_minute = (alarm_minute + 1*increment) % 60
            elif switch.value() == True:
                alarm_minute = (alarm_minute - 1*increment) % 60
            
        elif state == 33: # alarm
            snooze_minute = (snooze_minute - (1*increment))
            if snooze_minute < 1:
                snooze_minute += 60
            
        elif state == 4: # radio
            state = 43
        
        elif state == 42: # decrease radio frequency
            radio_frequency = radio_frequency - (0.1*increment)

            if ( fm_radio.SetFrequency( radio_frequency ) == True ):
                fm_radio.ProgramRadio()
                
        elif state == 43: # decrease radio volume
            radio_volume = (radio_volume - (1*increment)) % 16

            if ( fm_radio.SetVolume( radio_volume ) == True ):
                fm_radio.ProgramRadio()
        
            
def button_4_handler(pin): # functions of button 3
    global button_4_pressed
    global state
    global increment
    global increment_pointer
    global mute_status
    global alarm_set
    if not button_4_pressed:
        print("Button 4")
        button_4_pressed = True
        
        if state == 0: # main menu
            state = 4
        
        elif state == 1: # time format
            print("N/A") # No function assigned
            
        elif state == 2: # change time
            increment_function()
            
        elif state == 3: # alarm
            alarm_set = False
            state = 0
        
        elif state == 32: # alarm
            increment_function()
            
        elif state == 33: # alarm
            increment_function()
        
        elif state == 4: # radio
            if mute_status == True:
                mute_status = False
            else:
                mute_status = True
        
            if ( fm_radio.SetMute( mute_status ) == True ):
                fm_radio.ProgramRadio()
        
        elif state == 42: # trigger increment function to go up
            increment_function()
            
        elif state == 43: # trigger increment function to go up
            increment_function()

# interrupts for directing button presses
button_1.irq(trigger=machine.Pin.IRQ_FALLING, handler=button_1_handler)
button_2.irq(trigger=machine.Pin.IRQ_FALLING, handler=button_2_handler)
button_3.irq(trigger=machine.Pin.IRQ_FALLING, handler=button_3_handler)
button_4.irq(trigger=machine.Pin.IRQ_FALLING, handler=button_4_handler)
        



            
while ( True ):
    
#
# Clear the buffer
#
    oled.fill(0)
    
    utime.sleep(1); # tracks time by the second and allows for debouncing
    second +=1 ;
    
# basic function of a running clock
    if second >= 60:
        minute += 1;
        second = 0;
        
        if (hour == 11 or hour == 24) and minute == 60:
            if period == 'AM':
                period = 'PM'
            else:
                period = 'AM'
        
        if minute >= 60:
            hour += 1
            minute = 0;

            if format == 12 and hour > 12:
                hour = 1;
            if format == 24 and hour > 23:
                hour = 0;

#screen once alarm is triggered
    if (alarm_set == True) and (alarm_hour == hour) and (alarm_minute == minute) and (state != 32):
        state = 5
        if format == 12 and (alarm_period == period):
            formatted_time = "{:02}:{:02} {}".format(hour, minute, period)
            oled.text(formatted_time, 32, 16);
            oled.text("PST", 104, 16)
            oled.text("ALARM", 48, 32);
            oled.text("[1] Accept ", 12, 46);
            oled.text("[2] Snooze:%d " %snooze_minute, 12, 54);
            # Play Alarm
            radio_volume = 15
            if ( fm_radio.SetVolume( radio_volume ) == True ):
                fm_radio.ProgramRadio()
            mute_status = False
            if ( fm_radio.SetMute( mute_status ) == True ):
                fm_radio.ProgramRadio()
            # Mute/ stop radio
        elif format == 24:
            formatted_time = "{:02}:{:02}".format(hour, minute)
            oled.text(formatted_time, 44, 16);
            oled.text("PST", 104, 16)
            oled.text("ALARM", 48, 32);
            oled.text("[1] Accept ", 12, 46);
            oled.text("[2] Snooze:%d " %snooze_minute, 12, 54);
            # Play Alarm
            radio_volume = 15
            if ( fm_radio.SetVolume( radio_volume ) == True ):
                fm_radio.ProgramRadio()
            mute_status = False
            if ( fm_radio.SetMute( mute_status ) == True ):
                fm_radio.ProgramRadio()
            # Mute/ stop radio
# various screens that are displayed depending on the current state
# contains the relevant information for said state
    elif format == 12 and state == 0:
        formatted_time = "{:02}:{:02} {}".format(hour, minute, period)
        oled.text(formatted_time, 32, 16);
        alarm_set_notification()
        oled.text("PST", 104, 16)
        formatted_info = "V:{:02} S:{:05.1f}".format(radio_volume, radio_frequency)
        oled.text(formatted_info, 12, 34);
        oled.text("[F] [T] [A] [R]", 4, 50);
    elif format == 24 and state == 0:
        formatted_time = "{:02}:{:02}".format(hour, minute)
        oled.text(formatted_time, 44, 16);
        alarm_set_notification()
        oled.text("PST", 104, 16)
        formatted_info = "V:{:02} S:{:05.1f}".format(radio_volume, radio_frequency)
        oled.text(formatted_info, 12, 34);
        oled.text("[F] [T] [A] [R]", 4, 50);
    elif state == 1:
        oled.text("Change Format", 12, 0);
        oled.text("[1] Back ", 12, 30);
        oled.text("[2] 12 ", 12, 38);
        oled.text("[3] 24 ", 12, 46);
        oled.text("[4] N/A ", 12, 54);
    elif state == 2:
        oled.text("Change Time", 12, 0);
        if format == 12:
            formatted_time = "{:02}:{:02} {}".format(hour, minute, period)
            oled.text(formatted_time, 32, 16);
        elif format == 24:
            formatted_time = "{:02}:{:02}".format(hour, minute)
            oled.text(formatted_time, 44, 16);
        oled.text("[1] Back ", 12, 30);
        if switch.value() == False:
            oled.text("[2] +Hour ", 12, 38);
            oled.text("[3] +Min ", 12, 46);
        elif switch.value() == True:
            oled.text("[2] -Hour ", 12, 38);
            oled.text("[3] -Min ", 12, 46);
        oled.text("[4] Inc:%d" %increment, 12, 54)
    elif state == 3:
        oled.text("Alarm Menu", 12, 0);
        if format == 12:
            formatted_time = "{:02}:{:02} {}".format(alarm_hour, alarm_minute, alarm_period)
            oled.text(formatted_time, 32, 16);
        elif format == 24:
            formatted_time = "{:02}:{:02}".format(alarm_hour, alarm_minute)
            oled.text(formatted_time, 44, 16);
        oled.text("[1] Back ", 12, 30);
        if(alarm_set == True):
            oled.text("[2] Edit Alarm", 12, 38);
        else:
            oled.text("[2] Add Alarm", 12, 38);
        oled.text("[3] Snooze ", 12, 46);
        oled.text("[4] Delete ", 12, 54);
    elif state == 32:
        if(alarm_set == True):
            oled.text("Edit Alarm", 12, 0);
        else:
            oled.text("Add Alarm", 12, 0);
        if format == 12:
            formatted_time = "{:02}:{:02} {}".format(alarm_hour, alarm_minute, alarm_period)
            oled.text(formatted_time, 32, 16);
        elif format == 24:
            formatted_time = "{:02}:{:02}".format(alarm_hour, alarm_minute)
            oled.text(formatted_time, 44, 16);
        oled.text("[1] Confirm ", 12, 30);
        if switch.value() == False:
            oled.text("[2] +Hour ", 12, 38);
            oled.text("[3] +Min ", 12, 46);
        elif switch.value() == True:
            oled.text("[2] -Hour ", 12, 38);
            oled.text("[3] -Min ", 12, 46);
        oled.text("[4] Inc:%d" %increment, 12, 54)
    elif state == 33:
        oled.text("Edit Snooze", 12, 0);
        oled.text("Time: %d" %snooze_minute, 12, 16);
        oled.text("[1] Back ", 12, 30);
        oled.text("[2] +Min ", 12, 38);
        oled.text("[3] -Min ", 12, 46);
        oled.text("[4] Inc:%d" %increment, 12, 54)
    elif state == 4:
        oled.text("Radio Menu", 12, 0);
        formatted_info = "V:{:02} S:{:05.1f}".format(radio_volume, radio_frequency)
        oled.text(formatted_info, 12, 16);
        oled.text("[1] Back ", 12, 30);
        oled.text("[2] Station ", 12, 38);
        oled.text("[3] Sound ", 12, 46);
        if(mute_status == True):
            oled.text("[4] Unmute ", 12, 54);
        else:
            oled.text("[4] Mute ", 12, 54);
    elif state == 42:
        oled.text("Radio Station", 12, 0);
        formatted_info = "V:{:02} S:{:05.1f}".format(radio_volume, radio_frequency)
        oled.text(formatted_info, 12, 16);
        oled.text("[1] Back ", 12, 30);
        oled.text("[2] +Freq ", 12, 38);
        oled.text("[3] -Freq ", 12, 46);
        oled.text("[4] Inc:%d" %increment, 12, 54)
    elif state == 43:
        oled.text("Radio Sound", 12, 0);
        formatted_info = "V:{:02} S:{:05.1f}".format(radio_volume, radio_frequency)
        oled.text(formatted_info, 12, 16);
        oled.text("[1] Back ", 12, 30);
        oled.text("[2] +Vol ", 12, 38);
        oled.text("[3] -Vol ", 12, 46);
        oled.text("[4] Inc:%d" %increment, 12, 54)
       
    # Reset button press flag
    button_1_pressed = False
    button_2_pressed = False
    button_3_pressed = False
    button_4_pressed = False

# Transfer the buffer to the screen
    oled.show()
