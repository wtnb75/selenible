FROM python:3
ARG PJS_VER=2.1.1
RUN apt update && \
    apt install -y fontconfig ca-certificates bzip2 curl fonts-ipafont && \
    apt clean all
RUN fc-cache
RUN pip install jupyter
RUN pip install selenible
RUN jupyter kernelspec install /usr/local/lib/python3.6/site-packages/selenible/seleniblepiter
RUN curl -L https://bitbucket.org/ariya/phantomjs/downloads/phantomjs-${PJS_VER}-linux-x86_64.tar.bz2 | \
    tar xj --strip-components=1 -C /usr/local phantomjs-${PJS_VER}-linux-x86_64/bin/phantomjs
RUN useradd jupyter
EXPOSE 8888
USER jupyter
CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8888"]
