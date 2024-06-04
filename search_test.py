from youtubesearchpython import VideosSearch

videosSearch = VideosSearch('요네즈켄시', limit = 1)

print(videosSearch.result())

print(videosSearch.result()['result'][0]['link'])