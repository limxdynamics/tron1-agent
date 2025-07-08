import serial
 
ser = serial.Serial('/dev/wheeltec_mic', 115200)
 
def changehuan():
    head=0xA5
    userid=0x01
    msgtype=0x05
                                                            #唤醒词
    msg=b'{"type": "wakeup_keywords","content": {"keyword": "xiao3 chuang4 xiao3 chuang4","threshold": "500"}}\n'
    msglen_byte = len(msg).to_bytes(2, 'big') 
 
    msg_l = msglen_byte[1]
    msg_h= msglen_byte[0]
    msgid_l=0x01
    msgid_h=0x00
    checksum = ((~sum([head, userid, msgtype, msg_l, msg_h, msgid_l, msgid_h] + list(msg))) & 0xFF) +1
    head_byte = head.to_bytes(1, 'big')
    userid_byte = userid.to_bytes(1, 'big')
    msgtype_byte = msgtype.to_bytes(1, 'big')
    msg_l_byte = msg_l.to_bytes(1, 'big')
    msg_h_byte = msg_h.to_bytes(1, 'big')
    msgid_l_byte = msgid_l.to_bytes(1, 'big')
    msgid_h_byte = msgid_h.to_bytes(1, 'big')
    checksum_byte = checksum.to_bytes(1, 'big')
    complete_msg = head_byte + userid_byte + msgtype_byte + msg_l_byte + msg_h_byte + msgid_l_byte + msgid_h_byte + msg + checksum_byte
    return complete_msg
 
 
 
while 1:
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
    print(head,userid,msgtype,data_len,msgid,data,check)
    break
 
ser.write(changehuan())
 
while 1:
    head = ser.read(1).hex()
    if head == "a5":
        userid = ser.read(1).hex()
        msgtype = ser.read(1).hex()
 
        len_l=ser.read(1).hex()
        len_h=ser.read(1).hex() 
        data_len = int(len_h+len_l, 16)
 
        msgid = ser.read(2).hex()
        data = ser.read(data_len)
        check = ser.read(1).hex()
        if msgtype=="ff":
            print("更改完成 请重新上电")
            break
 
ser.close()