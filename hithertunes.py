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
            library = itunes.Library(parser.songs, parser.playlists)

            print "building sqlite3:   %s" % (self.database_location)
            cursor = self._sql_cursor()
            self._create_schema(cursor)
            self._parse_library(library, cursor)
            cursor.connection.commit()
            cursor.connection.close()

        print "using templates:    %s" % (templates_location,)

    def _sql_cursor(self):
        connection = sqlite3.connect(self.database_location)
        connection.row_factory = sqlite3.Row
        return connection.cursor()

    def _create_schema(self, cursor):
        try: 
            cursor.execute('''DROP TABLE songs''')
            cursor.execute('''DROP TABLE playlists''')
            cursor.execute('''DROP TABLE playlist_songs''')
        except: pass

        try: 
            cursor.execute('''CREATE TABLE songs (id INTEGER PRIMARY KEY, itunes_id INTEGER, name TEXT, artist TEXT, album TEXT, track_number INTEGER, year INTEGER, location TEXT)''')
            cursor.execute('''CREATE TABLE playlists (id INTEGER PRIMARY KEY, itunes_id INTEGER, name TEXT, visible INTEGER)''')
            cursor.execute('''CREATE TABLE playlist_songs (id INTEGER PRIMARY KEY, playlist_id INTEGER, song_id INTEGER, position INTEGER)''')
        except sqlite3.OperationalError, e:
            print e

    def _parse_library(self, library, cursor):
        for song in library.songs:
            if not song.artist or not song.album or not song.name: continue

            cursor.execute('''INSERT INTO songs (itunes_id, artist, album, name, track_number, year, location) VALUES (?, ?, ?, ?, ?, ?, ?)''', (song.itunes_id, song.artist, song.album, song.name, song.track_number, song.year, song.location))

        for playlist in library.playlists:
            if not playlist.name: continue
    
            # insert the playlists into the database
            cursor.execute('''INSERT INTO playlists (itunes_id, name, visible) VALUES (?, ?, ?)''', (playlist.itunes_id, playlist.name, False if playlist.visible == False else True))
            playlist_id = cursor.lastrowid

            # get the songs out of the playlist
            position = 0            
            for song in playlist.songs:
                cursor.execute('''SELECT id FROM songs WHERE itunes_id = ?''', (song.itunes_id,))                
                result = cursor.fetchone()
                song_id = result[0] if result else None

                if song_id: 
                    cursor.execute('''INSERT INTO playlist_songs (playlist_id, song_id, position) VALUES (?, ?, ?)''', (playlist_id, song_id, position))
                    position += 1

    @cherrypy.expose
    def index(self, playlist_id=None):
        """Display the whole library on one screen."""
        playlist_id = int(playlist_id) if playlist_id else 0

        cursor = self._sql_cursor()

        # if no playlist was chosen, display the entire library
        if not playlist_id:
            cursor.execute('''SELECT id, artist, album, name, track_number, year FROM songs ORDER BY LOWER(artist), COALESCE(year, 99999), LOWER(album), COALESCE(track_number, 99999), LOWER(name), id''')
        else:
            cursor.execute('''SELECT songs.id, artist, album, name, track_number, year FROM songs INNER JOIN playlist_songs ON playlist_songs.song_id = songs.id AND playlist_songs.playlist_id = ? ORDER BY position, songs.id''', (playlist_id,))
        songs = [x for x in cursor]

        cursor.execute('''SELECT id, name FROM playlists ORDER BY LOWER(name)''')
        playlists = [x for x in cursor]

        cursor.connection.close()

        template = self.template_lookup.get_template('index.mak')
        try: return template.render(songs=songs, playlists=playlists, selected_playlist_id=playlist_id)
        except: return exceptions.html_error_template().render()

    @cherrypy.expose
    def song(self, song_id):
        """Stream the bits of this song to the client."""
        cursor = self._sql_cursor()
        for row in cursor.execute('''SELECT location FROM songs WHERE id = ?''', (song_id,)):
            cherrypy.response.headers['Content-type'] = 'audio/mpeg'
            return urllib.urlopen(decode_unicode_references(row['location'])).read()


if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('--skip-rebuild-library', action='store_true', default=False)
    options, args = parser.parse_args()
    rebuild_library = not options.skip_rebuild_library

    itunes_exporter = iTunesExporter(library_location='~/Music/iTunes/iTunes Music Library.xml', 
                                     database_location='./library.sq3',
                                     templates_location=os.path.dirname(os.path.abspath(__file__)) + '/templates',
                                     rebuild_library=rebuild_library)
    cherrypy.config.update({'server.socket_host': '0.0.0.0',
                            'server.socket_port': 8085})
    cherrypy.tree.mount(itunes_exporter, '/', config={'/static': {'tools.staticdir.on': True,
                                                                  'tools.staticdir.dir': absolute_path('./static')}})
    cherrypy.quickstart()
