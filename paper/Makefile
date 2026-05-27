TEX := main.tex
FULL_TEX := main_full.tex
OUTDIR := build
TECTONIC ?= tectonic
TECTONIC_FLAGS ?= --keep-logs --keep-intermediates

.PHONY: pdf full clean

pdf:
	@command -v $(TECTONIC) >/dev/null || { \
		echo "tectonic not found. Activate the local environment with: conda activate cvpr-latex"; \
		exit 1; \
	}
	@mkdir -p $(OUTDIR)
	$(TECTONIC) $(TECTONIC_FLAGS) -o $(OUTDIR) $(TEX)

full:
	@command -v $(TECTONIC) >/dev/null || { \
		echo "tectonic not found. Activate the local environment with: conda activate cvpr-latex"; \
		exit 1; \
	}
	@mkdir -p $(OUTDIR)
	$(TECTONIC) $(TECTONIC_FLAGS) -o $(OUTDIR) $(FULL_TEX)

clean:
	rm -rf $(OUTDIR)
