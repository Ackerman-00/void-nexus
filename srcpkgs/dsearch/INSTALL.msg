dsearch requires initial configuration and index generation before starting the service.

1. Edit the configuration file:
   /etc/dsearch/config.toml

   At minimum, ensure:
   - index_path points to a writable location (e.g. /var/lib/dsearch/index)
   - at least one [[index_paths]] entry is defined

2. Generate the initial index (run as the dsearch user):
   sudo -u dsearch dsearch -c /etc/dsearch/config.toml index generate

3. Enable and start the service:
   ln -s /etc/sv/dsearch /var/service/
   sv up dsearch

4. Check logs if needed:
   tail -f /var/log/dsearch/current
