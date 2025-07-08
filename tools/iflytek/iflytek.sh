#CH9102，设置别名为wheeltec_mic
echo  'KERNEL=="ttyACM*", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="55d4",MODE:="0777", GROUP:="dialout", SYMLINK+="wheeltec_mic"' >>/etc/udev/rules.d/wheeltec_mic.rules

service udev reload
sleep 2
service udev restart


