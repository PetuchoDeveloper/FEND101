#Correcciones a el diagrama que se muestra en la imagen

1. el uso de epoll
no conocia el comando exacto que usaban los sockets de linux, lo cual es bastante util para entender como funciona el event loop, ya que espera a que epoll responda, pero en lo que este socket responde el sistema no se queda ocioso y puede realizar otras tareas hasta que epoll responda

2. yo tambien solia confundir paralelismo y concurrencia
despues de analizar el diagrama se ve claramente como un solo hilo puede realizar varias tareas si las organiza de forma inteligente, por lo que no es necesario en todos los casos tener mas de un hilo trabajando