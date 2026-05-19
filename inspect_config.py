import yaml
d = yaml.safe_load(open('/home/enomars/.hermes/config.yaml'))
print('Top-level keys:', list(d.keys()))
has_whatsapp = 'whatsapp' in d
has_platforms = 'platforms' in d
print('Has whatsapp:', has_whatsapp)
print('Has platforms:', has_platforms)
if has_platforms:
    print('Platforms keys:', list(d['platforms'].keys()))
    wp = d['platforms'].get('whatsapp', None)
    if wp:
        print('Whatsapp platforms config:', wp)
