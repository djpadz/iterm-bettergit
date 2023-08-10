SRC = bettergit/bettergit.py \
	  bettergit/git_poller.py \
	  bettergit/license.py \
	  bettergit/repo_status.py

ADDL_SRC = setup.cfg \
           metadata.json

TARGET = bettergit.its

SIGN = ${HOME}/.iterm2/it2sign
SIGNING_CERT = "Apple Development: Dj Padzensky (SDQF5T59D6)"


all: $(TARGET)

clean:
	rm -f $(TARGET) $(TARGET)-temp.zip

$(TARGET): $(SRC) $(ADDL_SRC)
	rm -f $(TARGET) $(TARGET)-temp.zip
	env COPYFILE_DISABLE=1 zip $(TARGET)-temp $(SRC) $(ADDL_SRC) > /dev/null
	$(SIGN) $(TARGET)-temp $(SIGNING_CERT) $(TARGET)
	rm -f $(TARGET)-temp
