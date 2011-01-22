<%!
  import json
  def js(string):
    return json.dumps(string).replace("'", "&#39;")
%>

<html>
  <head>
    <title>library :: hithertunes</title>

    <style type="text/css">
      body {padding:10px; margin:0}

      table {border-collapse:collapse}
      table tr td {font-family:arial; font-size:10pt; padding-right:5px solid #FFF}
      table tr:hover {cursor:pointer; background-color:#EEE}
      table tr.selected {background-color:#B4FFC1}

      div#playlist-header table {margin-top:10px}
      div#playlist-header tr {background-color: #DDD}
      div#playlist-header td {font-weight:bold}

      div#jp_playlist_1 {height:30px; overflow:hidden}
      div#playlist-header {position:fixed; top:0px; height:144px; left:0px; right:0px; overflow:auto; padding:10px 0 0 10px; background-color:#fff}
      div#playlist-container {padding-top:144px}
      li#song-name {cursor:pointer}
    </style>

  </head>

  <body>
    <div id="jplayer-container"></div>

    <div id="playlist-header">
      <div class="jp-audio">
	<div class="jp-type-single">
	  <div id="jp_interface_1" class="jp-interface">
	    <ul class="jp-controls">
	      <li><a href="#" class="jp-play" tabindex="1">play</a></li>
	      <li><a href="#" class="jp-pause" tabindex="1">pause</a></li>
	      <li><a href="#" class="jp-stop" tabindex="1">stop</a></li>
	      <li><a href="#" class="jp-mute" tabindex="1">mute</a></li>
	      <li><a href="#" class="jp-unmute" tabindex="1">unmute</a></li>
	    </ul>
	    <div class="jp-progress">
	      <div class="jp-seek-bar">
		<div class="jp-play-bar"></div>
	      </div>
	    </div>
	    <div class="jp-volume-bar">
	      <div class="jp-volume-bar-value"></div>
	    </div>
	    <div class="jp-current-time"></div>
	    <div class="jp-duration"></div>
	  </div>
	  <div id="jp_playlist_1" class="jp-playlist">
	    <ul>
	      <li id="song-name">Not Playing</li>
	    </ul>
	  </div>
	</div>
      </div>
      
      <table>
	<tr>
	  <td style="width:300px">artist</td>
	  <td style="width:334px" colspan="2">track</td>
	  <td style="width:351px" colspan="2">album</td>
	</tr>
      </table>
    </div>

    <div id="playlist-container">
    <table>
    % for song in songs:
      <tr id="song-row-${song['id']}" onclick='playSong("${song['id']}", ${song['artist'] | js}, ${song['name'] | js})'>
	<td style="width:300px">${song['artist']}</td>
	<td style="width:20px">${'%02d' % song['track_number'] if song['track_number'] else ''}</td>
	<td style="width:312px">${song['name']}</td>
	<td style="width:34px">${song['year'] if song['year'] else ''}</td>
	<td style="width:312px">${song['album']}</td>
      </tr>
    % endfor
    </table>
    </div>

    <script src="https://ajax.googleapis.com/ajax/libs/jquery/1.4.2/jquery.js"></script>    
    <script src="/static/jplayer/jquery.jplayer.min.js"></script>
    <link rel="stylesheet" type="text/css" href="/static/jplayer/jplayer.blue.monday.css">
    <script>
      function playSong(songId, artist, name) {
        $('#jplayer-container').jPlayer('setMedia', {mp3: '/song/' + songId}).jPlayer('play');
        $("#song-name").text(artist + " - " + name).click(function() { $(document).scrollTop($("#song-row-" + songId).offset().top - 180); });

        // update the table UI to indicate what's playing
        $("tr.selected").removeClass("selected")
        $("#song-row-" + songId).addClass("selected")
      }

      $(function() { 
          $("#jplayer-container").jPlayer({swfPath: '/static/jplayer',
                                           solution: 'flash, html',
                                           supplied: "mp3",
                                           });
      });
    </script>
  </body>
</html>
