import cherrypy
import os
import pyItunes as itunes
import re
import sqlite3
import urllib

from mako import exceptions
from mako.lookup import TemplateLookup
from mako.template import Template


def absolute_path(path):
    return os.path.abspath(os.path.expanduser(path))

def decode_unicode_references(data):
    def _callback(matches):
        id = matches.group(1)
        try:
            return unichr(int(id))
        except:
            return id
    return re.sub("&#(\d+)(;|(?=\s))", _callback, data)

class iTunesExporter(object):
    def __init__(self, database_location, templates_location, library_location, rebuild_library=False):
        self.database_location = absolute_path(database_location)
        self.template_lookup = TemplateLookup(directories=[templates_location])

        if rebuild_library:
            print "loading itunes:     %s" % (absolute_path(library_location),)
            parser = itunes.XMLLibraryParser(absolute_path(library_location))
            library = itunes.Library(parser.dictionary)

            print "building sqlite3:   %s" % (self.database_location)
            cursor = self._sql_cursor()
            self._create_schema(cursor)
            self._parse_library(library, cursor)
            cursor.connection.commit()
            cursor.connection.close()

    def _sql_cursor(self):
        connection = sqlite3.connect(self.database_location)
        connection.row_factory = sqlite3.Row
        return connection.cursor()

    def _create_schema(self, cursor):
        cursor.execute('''DROP TABLE songs''')
        try: cursor.execute('''CREATE TABLE songs (id INTEGER PRIMARY KEY, name TEXT, artist TEXT, album TEXT, track_number INTEGER, year INTEGER, location TEXT)''')
        except sqlite3.OperationalError, e: 
            print e   # don't go any further here; db exists already
            return

    def _parse_library(self, library, cursor):
        for song in library.songs:
            if not song.artist or not song.album or not song.name: continue

            cursor.execute('''INSERT INTO songs (artist, album, name, track_number, year, location) VALUES (?, ?, ?, ?, ?, ?)''', (song.artist, song.album, song.name, song.track_number, song.year, song.location))

    @cherrypy.expose
    def index(self):
        """Display the whole library on one screen."""
        cursor = self._sql_cursor()
        cursor.execute('''SELECT id, artist, album, name, track_number, year FROM songs ORDER BY LOWER(artist), COALESCE(year, 99999), LOWER(album), COALESCE(track_number, 99999), LOWER(name), id''')
        results = [x for x in cursor]
        template = self.template_lookup.get_template('index.mak')
        try: return template.render(songs=results)
        except: return exceptions.html_error_template().render()

        cursor.connection.close()

    @cherrypy.expose
    def song(self, song_id):
        """Stream the bits of this song to the client."""
        cursor = self._sql_cursor()
        for row in cursor.execute('''SELECT location FROM songs WHERE id = ?''', (song_id,)):
            cherrypy.response.headers['Content-type'] = 'audio/mpeg'
            print row['location']
            return urllib.urlopen(decode_unicode_references(row['location'])).read()


if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('--skip-rebuild-library', action='store_true', default=False)
    options, args = parser.parse_args()
    rebuild_library = not options.skip_rebuild_library

    itunes_exporter = iTunesExporter(library_location='~/Music/iTunes/iTunes Music Library.xml', 
                                     database_location='./library.sq3',
                                     templates_location=os.path.dirname(os.path.abspath(__file__)),
                                     rebuild_library=rebuild_library)
    cherrypy.config.update({'server.socket_host': '0.0.0.0',
                            'server.socket_port': 8085})
    cherrypy.tree.mount(itunes_exporter, '/', config={'/static': {'tools.staticdir.on': True,
                                                                  'tools.staticdir.dir': absolute_path('./static')}})
    cherrypy.quickstart()
