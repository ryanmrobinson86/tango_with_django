def encode_url(url):
    eurl = url.replace(' ','_')
    return eurl

def decode_url(url):
    durl = url.replace('_',' ')
    return durl
