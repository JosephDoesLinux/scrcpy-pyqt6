import subprocess
result = subprocess.run(['avahi-browse', '-r', '-t', '-p', '_adb-tls-connect._tcp'], capture_output=True, text=True)
print("OUT:", result.stdout)
print("ERR:", result.stderr)
