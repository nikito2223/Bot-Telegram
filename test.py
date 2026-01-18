import json

person = {
    "users": {
        "200": {
            "name": "test",
            "id": 0,
            "vip": True
        }
    }
}

ints = 200

data1 = person['users'][f'{ints}']['name'] = "lox"
 
with open('file.json', 'w') as json_file:
    json.dump(data1, json_file)

with open(f'./JSON/data/characters.json', 'r') as json_file:
    data = json.load(json_file)
    print(data)

{
    "users": {
        "6804554884": {
            "avatars": "D:/wamp64/www/BotPerson/avatars/profile-users\\6804554884.jpg",
            "name": "Фенрир | Semri Enigmos | Niko",
            "status": "defult user",
            "vip": false,
            "numberCharacters": 0,
            "koviks": 0
        }
    }
}