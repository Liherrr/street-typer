@echo off
rem Internal helper: opens the Windows firewall for Bit-Rate Brawl. Launched elevated by the main
rem launcher (and only once). Adds inbound rules for ALL network profiles (private + public) so the
rem opponent can reach this host regardless of how Windows classified the network.
netsh advfirewall firewall delete rule name="Bit-Rate Brawl" >nul 2>&1
netsh advfirewall firewall add rule name="Bit-Rate Brawl" dir=in action=allow protocol=TCP localport=8770,8780 profile=any
netsh advfirewall firewall delete rule name="Bit-Rate Brawl UDP" >nul 2>&1
netsh advfirewall firewall add rule name="Bit-Rate Brawl UDP" dir=in action=allow protocol=UDP localport=8771 profile=any
netsh advfirewall firewall delete rule name="Bit-Rate Brawl Ping" >nul 2>&1
netsh advfirewall firewall add rule name="Bit-Rate Brawl Ping" protocol=icmpv4:8,any dir=in action=allow profile=any
echo ok> "%~dp0.firewall_ok"
