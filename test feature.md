we want the client analytics opt in to be overriden by the value from the server

what we can do is as soon as server is connected, we call the /info endpoint on the server
and then we can set the value of the client analytics opt in to the value from the server

but what happens if we change the value in the server after the client is connected?

should we hit the /info endpoint periodically to check if the value has changed?
or can we ignore that case now, since the only use of this feature is in the managed-servers repo
and we will not be changing the value of the analytics opt in in the server, once it is set.

stages

- add the analytics opt in to the server info endpoint
- in the connect function, call a new override function that will set the value of the client
analytics opt in to the value from the server


questions

- should I override the get_store_info() function on the sql server to return the analytics?
- or should I enable this extra variable for all server types
- but this would mean more complexity as the user might expec the analytics opt-in value in the server to always reflect in the global config which in its current scope, it won't.
- is the RestZenStoreConfig a good place to add the analytics opt in?