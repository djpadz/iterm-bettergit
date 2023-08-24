SRC = bettergit/bettergit.py \
	  bettergit/config.py \
	  bettergit/git_poller.py \
	  bettergit/repo_status.py \
	  bettergit/logger.py

ADDL_SRC = setup.cfg \
           metadata.json

TARGET = bettergit.its

SIGN = ${HOME}/.iterm2/it2sign
SIGNING_CERT = "Apple Development: Dj Padzensky (SDQF5T59D6)"
INSTALL_DIR = "${HOME}/Library/Application Support/iTerm2/Scripts/AutoLaunch/bettergit"

all: $(TARGET)

clean:
	rm -rf $(TARGET) tmptmptmp

$(TARGET): $(SRC) $(ADDL_SRC)
	rm -rf tmptmptmp $(TARGET) $(TARGET)-temp.zip
	mkdir -p tmptmptmp/bettergit
	echo $(SRC) $(ADDL_SRC) | tr ' ' '\n' | cpio -pdumv tmptmptmp/bettergit
	(cd tmptmptmp && env COPYFILE_DISABLE=1 zip -r $(TARGET) bettergit)
	$(SIGN) tmptmptmp/$(TARGET) $(SIGNING_CERT) $(TARGET)
	rm -rf tmptmptmp

# This will overwrite the existing installation, but the existing installation must already exist.
install:
	@test -d $(INSTALL_DIR) || (echo "Existing installation doesn't exist.  Do the first installation by opening $(TARGET)" ; exit 1)
	echo $(SRC) $(ADDL_SRC) | tr ' ' '\n' | cpio -pdumv $(INSTALL_DIR)
