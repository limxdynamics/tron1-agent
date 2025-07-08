import serial
ser = serial.Serial('/dev/wheeltec_mic', 115200)
i=0
while i<20:
    head = ser.read(1).hex()
    if head != "a5":
        continue
    userid = ser.read(1).hex()
    msgtype = ser.read(1).hex()
    len_l=ser.read(1).hex()
    len_h=ser.read(1).hex() 
    data_len = int(len_h+len_l, 16)
    msgid = ser.read(2).hex()
    data = ser.read(data_len)
    check = ser.read(1).hex()
    print(msgtype,data)
    i+=1
ser.close()