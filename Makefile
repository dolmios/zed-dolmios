# Dolmios theme release tooling.
# Run `make help` for usage.

.PHONY: help validate version status release release-gh

THEME_FILE := themes/zed-dolmios.json
CURRENT_VERSION := $(shell grep '^version' extension.toml | sed 's/.*"\(.*\)"/\1/')

help:
	@echo "Dolmios theme release tooling"
	@echo ""
	@echo "Targets:"
	@echo "  make validate                            Validate theme JSON parses"
	@echo "  make version                             Print current version"
	@echo "  make status                              Show version + git status"
	@echo "  make release V=0.2.0 NOTES=\"summary\"     Bump, commit, tag, push"
	@echo "  make release-gh V=0.2.0 NOTES=\"summary\"  Create GitHub release for existing tag"

validate:
	@jq . $(THEME_FILE) > /dev/null && echo "OK $(THEME_FILE) valid"

version:
	@echo "$(CURRENT_VERSION)"

status:
	@echo "Version: $(CURRENT_VERSION)"
	@echo ""
	@git status -sb

# Bump version, prepend CHANGELOG entry, commit, tag, push.
# Usage: make release V=0.2.0 NOTES="syntax tweaks and ANSI fix"
release: validate
	@test -n "$(V)" || (echo "Error: pass V=x.y.z" && exit 1)
	@test -n "$(NOTES)" || (echo "Error: pass NOTES='summary text'" && exit 1)
	@echo "Bumping $(CURRENT_VERSION) to $(V)"
	@sed -i.bak 's/^version = "$(CURRENT_VERSION)"/version = "$(V)"/' extension.toml && rm extension.toml.bak
	@{ \
		head -n 1 CHANGELOG.md; \
		echo ""; \
		echo "## $(V)"; \
		echo ""; \
		echo "$(NOTES)"; \
		tail -n +2 CHANGELOG.md; \
	} > CHANGELOG.md.new && mv CHANGELOG.md.new CHANGELOG.md
	@git add extension.toml CHANGELOG.md $(THEME_FILE)
	@git commit -m "chore: release v$(V)"
	@git tag -a v$(V) -m "Release v$(V): $(NOTES)"
	@git push --follow-tags
	@echo "OK Released v$(V). Next: make release-gh V=$(V) NOTES=\"$(NOTES)\""

# Create GitHub release for an existing tag.
# Usage: make release-gh V=0.2.0 NOTES="summary"
release-gh:
	@test -n "$(V)" || (echo "Error: pass V=x.y.z" && exit 1)
	@test -n "$(NOTES)" || (echo "Error: pass NOTES='summary text'" && exit 1)
	@gh release create v$(V) --title "v$(V)" --notes "$(NOTES)"
	@echo "OK Created GitHub release v$(V)"
