.PHONY: docker build clean
docker: selenium-server configs scripts
	rm -f *.tar.gz
	tar -czf configs.tar.gz configs
	tar -czf scripts.tar.gz scripts
	tar -czf selenium-server.tar.gz selenium-server

build: configs.tar.gz scripts.tar.gz selenium-server.tar.gz Dockerfile
	docker build -t r2g:alpha .

clean:
	rm -f *.tar.gz
