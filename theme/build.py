#!/usr/bin/env python3
"""Generate the Greenpuccin VSCodium colour themes from the Figcraft variables export.

    python3 -I theme/build.py [path/to/Greenpuccin.variables.json]

Writes theme/greenpuccin/ (a local extension: package.json + one theme per mode).
Every value in the output comes from the Greenpuccin palette, optionally with an alpha
channel, or is fully transparent (#00000000). The themes have no "include", and every
colour key VSCodium registers is set explicitly, so nothing falls back to a built-in theme.

How each workbench colour is chosen, in order:
  1. EXPLICIT below: the hand-made design (flat surfaces, no dividers, green accent).
  2. VSCodium's own default for the key (tools/vscode-color-defaults.json), resolved against
     this theme: references follow the other keys, transparency is kept, lighten/darken steps
     one shade along the ramp, and any literal hex snaps to the nearest palette colour (OKLab).
  3. Name-based FALLBACK for the few defaults the extractor couldn't parse.

Value specs used in the tables:  "<token>"  or  "<token>@<alpha %>"  or  "none" (transparent).
A token is any variable name from the export ("ramp/base", "accent/green") or a semantic alias
("Surface", "Primary", "Text muted"...). A dict {"dark": spec, "light": spec} varies by mode.
"""
import json, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXPORT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "Greenpuccin.variables.json")
DEFAULTS = os.path.join(HERE, "tools", "vscode-color-defaults.json")
OUT = os.path.join(HERE, "greenpuccin")
MODES = {"Matcha": "dark", "Sencha": "light"}  # Figma mode name -> VSCodium theme type
RAMP = ["crust", "mantle", "base", "surface0", "surface1", "surface2",
        "overlay0", "overlay1", "overlay2", "subtext0", "subtext1", "text"]

# ---------------------------------------------------------------------------------------------
# 1. The design. Anything not listed is derived from VSCodium's defaults (see module docstring).
# ---------------------------------------------------------------------------------------------
NONE = "none"
EXPLICIT = {
    # ---- base text ----
    "foreground": "Text",
    "strongForeground": "Text",
    "descriptionForeground": "Text muted",
    "disabledForeground": "ramp/overlay1",
    "errorForeground": "Danger",
    "icon.foreground": "ramp/subtext1",
    "focusBorder": "Primary@50",
    "contrastBorder": NONE,
    "contrastActiveBorder": NONE,
    "selection.background": "Primary@25",
    "textLink.foreground": "accent-text/blue",
    "textLink.activeForeground": "accent-text/lavender",
    "textPreformat.foreground": "accent-text/peach",
    "textPreformat.background": "Surface raised",
    "textBlockQuote.background": "Surface sunken",
    "textBlockQuote.border": "Border",
    "textCodeBlock.background": "Surface sunken",
    "textSeparator.foreground": "Border",

    # ---- surfaces: one flat Surface everywhere (reads as a single pane under Hyprland blur) ----
    "editor.background": "Surface",
    "editor.foreground": "Text",
    "editorGutter.background": "Surface",
    "editorPane.background": "Surface",
    "sideBar.background": "Surface",
    "sideBar.foreground": "ramp/subtext1",
    "sideBarTitle.foreground": "Text muted",
    "sideBarSectionHeader.background": "Surface",
    "sideBarSectionHeader.foreground": "Text muted",
    "activityBar.background": "Surface",
    "activityBar.foreground": "Text",
    "activityBar.inactiveForeground": "ramp/overlay1",
    "activityBar.activeBorder": "Primary",
    "activityBarTop.foreground": "Text",
    "activityBarTop.inactiveForeground": "ramp/overlay1",
    "activityBarTop.activeBorder": "Primary",
    "panel.background": "Surface",
    "panelTitle.activeForeground": "Text",
    "panelTitle.inactiveForeground": "ramp/overlay1",
    "panelTitle.activeBorder": "Primary",
    "terminal.background": "Surface",
    "terminal.foreground": "Text",
    "statusBar.background": "Surface",
    "statusBar.foreground": "Text muted",
    "statusBar.noFolderBackground": "Surface",
    "statusBar.noFolderForeground": "Text muted",
    "statusBar.debuggingBackground": "Surface",
    "statusBar.debuggingForeground": "accent/peach",
    "statusBarItem.remoteBackground": NONE,
    "statusBarItem.remoteForeground": "Text muted",
    "statusBarItem.hoverBackground": "Surface raised",
    "statusBarItem.activeBackground": "ramp/surface1",
    "statusBarItem.prominentBackground": "Surface raised",
    "statusBarItem.errorBackground": NONE,
    "statusBarItem.errorForeground": "Danger",
    "statusBarItem.warningBackground": NONE,
    "statusBarItem.warningForeground": "accent-text/yellow",
    "titleBar.activeBackground": "Surface",
    "titleBar.activeForeground": "Text",
    "titleBar.inactiveBackground": "Surface",
    "titleBar.inactiveForeground": "ramp/overlay1",
    "menubar.selectionBackground": "Surface raised",
    "editorGroupHeader.tabsBackground": "Surface",
    "editorGroupHeader.noTabsBackground": "Surface",
    "tab.activeBackground": "Surface",
    "tab.unfocusedActiveBackground": "Surface",
    "tab.activeForeground": "Text",
    "tab.unfocusedActiveForeground": "Text muted",
    "tab.inactiveBackground": "Surface",
    "tab.unfocusedInactiveBackground": "Surface",
    "tab.inactiveForeground": "ramp/overlay1",
    "tab.unfocusedInactiveForeground": "ramp/overlay1",
    "tab.hoverBackground": "Surface raised",
    "tab.unfocusedHoverBackground": "Surface raised",
    "tab.activeModifiedBorder": "accent/peach",
    "tab.selectedBackground": "Surface raised",
    "tab.selectedForeground": "Text",
    "breadcrumb.background": "Surface",

    # ---- raised surfaces: menus, pickers, hovers, widgets ----
    "editorWidget.background": "Surface raised",
    "editorWidget.foreground": "Text",
    "editorWidget.border": NONE,
    "editorHoverWidget.background": "Surface raised",
    "editorHoverWidget.border": NONE,
    "editorHoverWidget.statusBarBackground": "ramp/surface1",
    "editorSuggestWidget.background": "Surface raised",
    "editorSuggestWidget.border": NONE,
    "editorSuggestWidget.foreground": "Text",
    "editorSuggestWidget.selectedBackground": "ramp/surface1",
    "editorSuggestWidget.selectedForeground": "Text",
    "editorSuggestWidget.highlightForeground": "Primary",
    "editorSuggestWidget.focusHighlightForeground": "Primary",
    "quickInput.background": "Surface raised",
    "quickInput.foreground": "Text",
    "quickInputTitle.background": "ramp/surface1",
    "quickInputList.focusBackground": "ramp/surface1",
    "quickInputList.focusForeground": "Text",
    "quickInputList.focusIconForeground": "Text",
    "pickerGroup.foreground": "Primary",
    "pickerGroup.border": "Border@40",
    "list.highlightForeground": "Primary",
    "list.focusHighlightForeground": "Primary",
    "menu.background": "Surface raised",
    "menu.foreground": "Text",
    "menu.selectionBackground": "ramp/surface1",
    "menu.selectionForeground": "Text",
    "menu.separatorBackground": "ramp/surface2",
    "menu.border": NONE,
    "notifications.background": "Surface raised",
    "notifications.foreground": "Text",
    "notifications.border": NONE,
    "notificationCenterHeader.background": "Surface raised",
    "notificationCenter.border": NONE,
    "notificationToast.border": NONE,
    "notificationLink.foreground": "accent-text/blue",
    "notificationsErrorIcon.foreground": "Danger",
    "notificationsWarningIcon.foreground": "accent-text/yellow",
    "notificationsInfoIcon.foreground": "accent-text/blue",
    "input.background": "Surface sunken",
    "input.foreground": "Text",
    "input.placeholderForeground": "ramp/overlay1",
    "input.border": NONE,
    "inputOption.activeBorder": "Primary",
    "inputOption.activeBackground": "Primary@20",
    "inputOption.activeForeground": "Text",
    "inputValidation.errorBackground": "Surface sunken",
    "inputValidation.errorBorder": "Danger",
    "inputValidation.errorForeground": "Text",
    "inputValidation.warningBackground": "Surface sunken",
    "inputValidation.warningBorder": "accent/yellow",
    "inputValidation.warningForeground": "Text",
    "inputValidation.infoBackground": "Surface sunken",
    "inputValidation.infoBorder": "accent/blue",
    "inputValidation.infoForeground": "Text",
    "dropdown.background": "Surface sunken",
    "dropdown.listBackground": "Surface raised",
    "dropdown.foreground": "Text",
    "dropdown.border": NONE,
    "list.hoverBackground": "Surface raised",
    "list.hoverForeground": "Text",
    "list.activeSelectionBackground": "ramp/surface1",
    "list.activeSelectionForeground": "Text",
    "list.activeSelectionIconForeground": "Text",
    "list.inactiveSelectionBackground": "Surface raised",
    "list.inactiveSelectionForeground": "Text",
    "list.focusBackground": "ramp/surface1",
    "list.focusForeground": "Text",
    "list.focusOutline": NONE,
    "list.inactiveFocusOutline": NONE,
    "list.dropBackground": "Primary@15",
    "list.errorForeground": "Danger",
    "list.warningForeground": "accent-text/yellow",
    "list.invalidItemForeground": "Danger",
    "list.deemphasizedForeground": "ramp/overlay1",
    "list.filterMatchBackground": "accent/peach@25",
    "list.filterMatchBorder": NONE,
    "tree.indentGuidesStroke": "ramp/surface2",
    "tree.inactiveIndentGuidesStroke": "ramp/surface1",
    "keybindingLabel.background": "Surface sunken",
    "keybindingLabel.foreground": "Text",
    "keybindingLabel.border": NONE,
    "keybindingLabel.bottomBorder": "Border@40",
    "peekView.border": "Primary",
    "peekViewTitle.background": "Surface raised",
    "peekViewTitleLabel.foreground": "Text",
    "peekViewTitleDescription.foreground": "Text muted",
    "peekViewEditor.background": "Surface sunken",
    "peekViewEditorGutter.background": "Surface sunken",
    "peekViewResult.background": "Surface raised",
    "peekViewResult.selectionBackground": "ramp/surface1",
    "peekViewResult.selectionForeground": "Text",
    "peekViewResult.fileForeground": "Text",
    "peekViewResult.lineForeground": "Text muted",
    "peekViewResult.matchHighlightBackground": "accent/peach@25",
    "peekViewEditor.matchHighlightBackground": "accent/peach@25",

    # ---- primary (green) ----
    "button.background": "Primary",
    "button.foreground": "On primary",
    "button.hoverBackground": "Primary hover",
    "button.border": NONE,
    "button.separator": "On primary@40",
    "button.secondaryBackground": "ramp/surface1",
    "button.secondaryForeground": "Text",
    "button.secondaryHoverBackground": "ramp/surface2",
    "button.secondaryBorder": NONE,
    "extensionButton.prominentBackground": "Primary",
    "extensionButton.prominentForeground": "On primary",
    "extensionButton.prominentHoverBackground": "Primary hover",
    "badge.background": "Primary",
    "badge.foreground": "On primary",
    "activityBarBadge.background": "Primary",
    "activityBarBadge.foreground": "On primary",
    "progressBar.background": "Primary",
    "checkbox.background": "Surface sunken",
    "checkbox.foreground": "Text",
    "checkbox.border": "Border",
    "checkbox.selectBackground": "Surface sunken",
    "checkbox.selectBorder": "Primary",
    "radio.activeBackground": "Primary@20",
    "radio.activeForeground": "Text",
    "radio.activeBorder": "Primary",
    "editorCursor.foreground": "Primary",
    "terminalCursor.foreground": "Primary",
    "activityWarningBadge.background": "accent/yellow",
    "activityWarningBadge.foreground": "ramp/crust",
    "activityErrorBadge.background": "Danger",
    "activityErrorBadge.foreground": "ramp/crust",
    "chat.linesAddedForeground": "accent-text/green",
    "chat.linesRemovedForeground": "accent-text/red",
    "scmGraph.historyItemHoverAdditionsForeground": "accent-text/green",
    "scmGraph.historyItemHoverDeletionsForeground": "accent-text/red",
    "panelSectionHeader.background": "Surface",
    "editorMultiCursor.primary.foreground": "Primary",
    "editorMultiCursor.secondary.foreground": "accent/teal",
    "settings.headerForeground": "Text",
    "settings.modifiedItemIndicator": "Primary",
    "settings.focusedRowBackground": "Surface raised@50",
    "settings.rowHoverBackground": "Surface raised@50",
    "settings.focusedRowBorder": NONE,
    "welcomePage.progress.foreground": "Primary",
    "walkThrough.embeddedEditorBackground": "Surface sunken",

    # ---- no dividers ----
    "titleBar.border": NONE,
    "activityBar.border": NONE,
    "sideBar.border": NONE,
    "sideBarSectionHeader.border": NONE,
    "sideBarActivityBarTop.border": NONE,
    "panel.border": NONE,
    "panelSectionHeader.border": NONE,
    "panelSection.border": NONE,
    "statusBar.border": NONE,
    "statusBar.focusBorder": NONE,
    "statusBar.noFolderBorder": NONE,
    "statusBarItem.focusBorder": NONE,
    "tab.border": NONE,
    "tab.activeBorderTop": NONE,
    "tab.unfocusedActiveBorderTop": NONE,
    "tab.activeBorder": "Primary",               # thin accent under the active tab instead of above
    "tab.unfocusedActiveBorder": NONE,
    "tab.hoverBorder": NONE,
    "tab.selectedBorderTop": NONE,
    "editorGroupHeader.tabsBorder": NONE,
    "editorGroupHeader.border": NONE,
    "editorGroup.border": "Border@25",           # keep a faint seam between split editors
    "breadcrumbPicker.background": "Surface raised",
    "scrollbar.shadow": NONE,
    "widget.shadow": "ramp/crust@50",
    "widget.border": NONE,
    "sash.hoverBorder": "Primary@50",

    # ---- quieter editor furniture ----
    "editorLineNumber.foreground": "ramp/surface2",
    "editorLineNumber.activeForeground": "Text muted",
    "editorLineNumber.dimmedForeground": "ramp/surface1",
    "editorIndentGuide.background1": "Text@4",
    "editorIndentGuide.activeBackground1": "Text@14",
    "editorWhitespace.foreground": "ramp/surface2",
    "editorRuler.foreground": "ramp/surface1",
    "editor.lineHighlightBackground": NONE,
    "editor.lineHighlightBorder": NONE,
    "editor.selectionBackground": "ramp/overlay2@25",
    "editor.selectionForeground": NONE,
    "editor.inactiveSelectionBackground": "ramp/overlay2@15",
    "editor.selectionHighlightBackground": "ramp/overlay2@15",
    "editor.wordHighlightBackground": "ramp/overlay2@15",
    "editor.wordHighlightStrongBackground": "ramp/overlay2@25",
    "editor.wordHighlightTextBackground": "ramp/overlay2@15",
    "editor.findMatchBackground": "accent/peach@40",
    "editor.findMatchHighlightBackground": "accent/peach@20",
    "editor.findRangeHighlightBackground": "ramp/overlay2@10",
    "editor.rangeHighlightBackground": "ramp/overlay2@10",
    "editor.symbolHighlightBackground": "accent/peach@20",
    "editor.hoverHighlightBackground": "ramp/overlay2@15",
    "editor.foldBackground": "ramp/overlay2@10",
    "editorBracketMatch.background": "ramp/overlay2@15",
    "editorBracketMatch.border": NONE,
    "editorLink.activeForeground": "accent-text/blue",
    "editorCodeLens.foreground": "ramp/overlay1",
    "editorInlayHint.background": "Surface raised@60",
    "editorInlayHint.foreground": "ramp/overlay2",
    "editorGhostText.foreground": "ramp/overlay1",
    "editorUnnecessaryCode.opacity": "ramp/crust@67",  # only the alpha is used (fades unused code)
    "editorStickyScroll.background": "Surface",
    "editorStickyScroll.shadow": "ramp/crust@50",
    "scrollbarSlider.background": "Text@8",
    "scrollbarSlider.hoverBackground": "Text@14",
    "scrollbarSlider.activeBackground": "Text@20",
    "minimapSlider.background": "Text@8",
    "minimapSlider.hoverBackground": "Text@14",
    "minimapSlider.activeBackground": "Text@20",
    "editorBracketHighlight.foreground1": "accent-text/mauve",
    "editorBracketHighlight.foreground2": "accent-text/blue",
    "editorBracketHighlight.foreground3": "accent-text/peach",
    "editorBracketHighlight.foreground4": "accent-text/teal",
    "editorBracketHighlight.foreground5": "accent-text/pink",
    "editorBracketHighlight.foreground6": "accent-text/yellow",
    "editorBracketHighlight.unexpectedBracket.foreground": "Danger",

    # ---- diagnostics, diff, git ----
    "editorError.foreground": "Danger",
    "editorWarning.foreground": "accent-text/yellow",
    "editorInfo.foreground": "accent-text/blue",
    "editorHint.foreground": "accent-text/teal",
    "editorOverviewRuler.border": NONE,
    "editorOverviewRuler.errorForeground": "Danger",
    "editorOverviewRuler.warningForeground": "accent/yellow",
    "editorOverviewRuler.infoForeground": "accent/blue",
    "editorGutter.addedBackground": "accent/green",
    "editorGutter.modifiedBackground": "accent/yellow",
    "editorGutter.deletedBackground": "accent/red",
    "editorOverviewRuler.addedForeground": "accent/green@60",
    "editorOverviewRuler.modifiedForeground": "accent/yellow@60",
    "editorOverviewRuler.deletedForeground": "accent/red@60",
    "minimapGutter.addedBackground": "accent/green",
    "minimapGutter.modifiedBackground": "accent/yellow",
    "minimapGutter.deletedBackground": "accent/red",
    "diffEditor.insertedTextBackground": "accent/green@15",
    "diffEditor.removedTextBackground": "accent/red@15",
    "diffEditor.insertedLineBackground": "accent/green@10",
    "diffEditor.removedLineBackground": "accent/red@10",
    "diffEditor.border": NONE,
    "diffEditor.diagonalFill": "ramp/surface1@60",
    "gitDecoration.addedResourceForeground": "accent-text/green",
    "gitDecoration.untrackedResourceForeground": "accent-text/green",
    "gitDecoration.modifiedResourceForeground": "accent-text/yellow",
    "gitDecoration.stageModifiedResourceForeground": "accent-text/yellow",
    "gitDecoration.deletedResourceForeground": "accent-text/red",
    "gitDecoration.stageDeletedResourceForeground": "accent-text/red",
    "gitDecoration.renamedResourceForeground": "accent-text/teal",
    "gitDecoration.conflictingResourceForeground": "accent-text/mauve",
    "gitDecoration.ignoredResourceForeground": "ramp/overlay0",
    "gitDecoration.submoduleResourceForeground": "accent-text/blue",
    "merge.currentHeaderBackground": "accent/teal@40",
    "merge.currentContentBackground": "accent/teal@15",
    "merge.incomingHeaderBackground": "accent/blue@40",
    "merge.incomingContentBackground": "accent/blue@15",
    "merge.commonHeaderBackground": "ramp/overlay2@40",
    "merge.commonContentBackground": "ramp/overlay2@15",
    "merge.border": NONE,

    # ---- terminal ----
    "terminal.border": NONE,
    "terminal.selectionBackground": "ramp/overlay2@25",
    "terminal.findMatchBackground": "accent/peach@40",
    "terminal.findMatchHighlightBackground": "accent/peach@20",
    "terminalCommandDecoration.defaultBackground": "ramp/overlay0",
    "terminalCommandDecoration.successBackground": "accent/green",
    "terminalCommandDecoration.errorBackground": "accent/red",
    # ANSI: accent/* is the normal set, bright/* the bright set (Catppuccin convention for the greys)
    "terminal.ansiBlack": {"dark": "ramp/surface1", "light": "ramp/subtext1"},
    "terminal.ansiRed": "accent/red",
    "terminal.ansiGreen": "accent/green",
    "terminal.ansiYellow": "accent/yellow",
    "terminal.ansiBlue": "accent/blue",
    "terminal.ansiMagenta": "accent/pink",
    "terminal.ansiCyan": "accent/teal",
    "terminal.ansiWhite": {"dark": "ramp/subtext1", "light": "ramp/surface2"},
    "terminal.ansiBrightBlack": {"dark": "ramp/surface2", "light": "ramp/subtext0"},
    "terminal.ansiBrightRed": "bright/red",
    "terminal.ansiBrightGreen": "bright/green",
    "terminal.ansiBrightYellow": "bright/yellow",
    "terminal.ansiBrightBlue": "bright/blue",
    "terminal.ansiBrightMagenta": "bright/magenta",
    "terminal.ansiBrightCyan": "bright/cyan",
    "terminal.ansiBrightWhite": {"dark": "ramp/subtext0", "light": "ramp/surface1"},
}

# Last resort for keys whose VSCodium default couldn't be parsed (first match wins).
FALLBACK = [
    (r"(Error|error)", "Danger"),
    (r"(Warning|warning)", "accent/yellow"),
    (r"Shadow$|shadow$", "ramp/crust@50"),
    (r"(Highlight|highlight).*Background$", "ramp/overlay2@15"),
    (r"(Border|border)$", NONE),
    (r"(Background|background)$", "Surface"),
    (r"", "Text"),
]

# ---------------------------------------------------------------------------------------------
# 2. Syntax. accent-text/* are the variants tuned for text contrast (identical to accent/* in Matcha).
# ---------------------------------------------------------------------------------------------
TOKENS = [  # (scopes, spec, fontStyle)
    (["comment", "punctuation.definition.comment", "string.comment"], "ramp/overlay1", "italic"),
    (["string", "string.quoted", "string.template", "markup.inline.raw", "markup.raw", "string.tag", "string.value",
      "meta.embedded.assembly"], "accent-text/green", None),
    (["constant.character.escape", "string.regexp", "constant.other.placeholder", "constant.character.format.placeholder"],
     "accent-text/pink", None),
    (["keyword", "keyword.control", "keyword.other", "keyword.operator.new", "keyword.operator.expression",
      "keyword.operator.logical.python", "keyword.operator.wordlike", "keyword.operator.noexcept",
      "keyword.operator.sizeof", "keyword.operator.delete", "keyword.other.using", "storage", "storage.type",
      "storage.modifier", "meta.preprocessor", "entity.name.function.preprocessor", "keyword.control.directive"],
     "accent-text/mauve", None),
    (["keyword.operator", "punctuation.accessor", "punctuation.separator.key-value", "punctuation.separator.namespace",
      "keyword.operator.quantifier.regexp", "keyword.operator.or.regexp", "keyword.control.anchor.regexp",
      "keyword.operator.negation.regexp"], "accent-text/sky", None),
    (["constant", "constant.numeric", "constant.language", "constant.other", "variable.other.constant",
      "keyword.other.unit", "constant.sha.git-rebase", "meta.preprocessor.numeric", "support.constant",
      "constant.character", "constant.other.option", "constant.other.color"], "accent-text/peach", None),
    (["variable.other.enummember", "constant.other.enum"], "accent-text/teal", None),
    (["entity.name.function", "support.function", "meta.function-call.generic", "entity.name.operator.custom-literal",
      "support.function.git-rebase", "variable.function"], "accent-text/blue", None),
    (["entity.name.type", "entity.name.class", "entity.name.struct", "entity.name.enum", "entity.name.interface",
      "support.type", "support.class", "entity.other.inherited-class", "entity.name.scope-resolution",
      "meta.type.cast.expr", "meta.type.new.expr", "entity.name.type.parameter", "storage.type.numeric.go",
      "storage.type.string.go", "storage.type.boolean.go", "storage.type.byte.go", "storage.type.error.go",
      "storage.type.rune.go", "storage.type.uintptr.go", "storage.type.cs", "storage.type.generic.cs",
      "storage.type.java", "storage.type.generic.java", "storage.type.primitive.java", "storage.type.object.array.java",
      "storage.type.primitive.array.java", "storage.type.annotation.java", "storage.type.groovy",
      "entity.other.attribute"], "accent-text/yellow", None),
    (["variable", "meta.definition.variable", "meta.definition.variable.name", "entity.name.variable",
      "support.variable", "meta.template.expression", "meta.embedded", "source.groovy.embedded",
      "storage.modifier.import.java", "storage.modifier.package.java", "variable.language.wildcard.java",
      "entity.name.label"], "Text", None),
    (["variable.parameter", "meta.parameter"], "accent-text/maroon", None),
    (["variable.language", "variable.language.this", "variable.language.self", "variable.language.super",
      "variable.legacy.builtin.python"], "accent-text/red", None),
    (["variable.other.property", "variable.other.object.property", "support.variable.property",
      "meta.object-literal.key", "meta.structure.dictionary.key.python", "support.type.property-name",
      "support.type.vendored.property-name", "entity.name.tag.yaml", "source.powershell variable.other.member"],
     "accent-text/lavender", None),
    (["entity.name.namespace", "entity.name.module", "entity.name.package"], "accent-text/rosewater", None),
    (["meta.decorator", "entity.name.function.decorator", "punctuation.decorator", "storage.type.annotation",
      "meta.attribute"], "accent-text/peach", None),
    (["punctuation.definition.template-expression.begin", "punctuation.definition.template-expression.end",
      "punctuation.section.embedded", "punctuation.section.embedded.begin.php",
      "punctuation.section.embedded.end.php"], "accent-text/pink", None),
    (["punctuation", "meta.brace", "punctuation.definition.tag", "punctuation.definition.group.regexp",
      "punctuation.character.set.begin.regexp", "punctuation.character.set.end.regexp"], "ramp/overlay2", None),
    (["constant.character.character-class.regexp", "constant.other.character-class.regexp",
      "constant.other.character-class.set.regexp", "constant.character.set.regexp", "constant.regexp"],
     "accent-text/peach", None),
    # markup / HTML / CSS
    (["entity.name.tag", "entity.name.tag.css", "entity.name.tag.less"], "accent-text/mauve", None),
    (["entity.other.attribute-name"], "accent-text/yellow", None),
    (["entity.other.attribute-name.class.css", "entity.other.attribute-name.id.css",
      "entity.other.attribute-name.pseudo-class.css", "entity.other.attribute-name.pseudo-element.css",
      "entity.other.attribute-name.parent-selector.css", "source.css entity.other.attribute-name.class",
      "entity.other.attribute-name.parent.less", "entity.other.attribute-name.scss"], "accent-text/yellow", None),
    (["support.constant.property-value", "support.constant.font-name", "support.constant.media-type",
      "support.constant.media", "constant.other.color.rgb-value", "constant.other.rgb-value"], "accent-text/peach", None),
    (["source.css variable", "source.coffee.embedded", "variable.css", "variable.scss"], "accent-text/lavender", None),
    (["markup.heading", "entity.name.section", "markup.heading.setext"], "accent-text/green", "bold"),
    (["markup.bold"], "accent-text/peach", "bold"),
    (["markup.italic"], "accent-text/maroon", "italic"),
    (["markup.strikethrough"], "ramp/overlay1", "strikethrough"),
    (["markup.underline.link", "string.other.link", "markup.underline"], "accent-text/blue", "underline"),
    (["markup.quote", "punctuation.definition.quote.begin.markdown"], "accent-text/pink", "italic"),
    (["markup.list", "punctuation.definition.list.begin.markdown", "beginning.punctuation.definition.list.markdown"],
     "accent-text/teal", None),
    (["string meta.image.inline.markdown"], "Text", None),
    (["markup.inserted", "meta.diff.header.to-file", "punctuation.definition.inserted"], "accent-text/green", None),
    (["markup.deleted", "meta.diff.header.from-file", "punctuation.definition.deleted"], "accent-text/red", None),
    (["markup.changed", "punctuation.definition.changed"], "accent-text/yellow", None),
    (["meta.diff.header", "meta.diff.range", "meta.separator", "header"], "accent-text/blue", None),
    (["markup.output", "markup.raw.block"], "Text muted", None),
    (["invalid", "invalid.illegal"], "Danger", None),
    (["invalid.deprecated"], "accent-text/mauve", "strikethrough"),
]

SEMANTIC = {
    "namespace": "accent-text/rosewater",
    "type": "accent-text/yellow", "class": "accent-text/yellow", "struct": "accent-text/yellow",
    "interface": "accent-text/yellow", "enum": "accent-text/yellow", "typeParameter": "accent-text/yellow",
    "enumMember": "accent-text/teal",
    "function": "accent-text/blue", "method": "accent-text/blue", "macro": "accent-text/peach",
    "decorator": "accent-text/peach",
    "parameter": "accent-text/maroon",
    "variable": "Text", "variable.readonly": "accent-text/peach", "variable.defaultLibrary": "accent-text/red",
    "property": "accent-text/lavender", "property.readonly": "accent-text/lavender",
    "keyword": "accent-text/mauve", "modifier": "accent-text/mauve",
    "comment": "ramp/overlay1", "string": "accent-text/green", "number": "accent-text/peach",
    "regexp": "accent-text/pink", "operator": "accent-text/sky", "label": "Text",
    "selfParameter": "accent-text/red", "selfKeyword": "accent-text/red",
    "*.deprecated": {"strikethrough": True},
}

# ---------------------------------------------------------------------------------------------
# Machinery
# ---------------------------------------------------------------------------------------------

def load_palette(path):
    data = json.load(open(path, encoding="utf-8"))["meta"]
    variables = {v["id"]: v for v in data["variables"].values() if v["resolvedType"] == "COLOR"}
    modes = {m["modeId"]: m["name"] for c in data["variableCollections"].values() for m in c["modes"]}

    def resolve(var, mode_id):
        val = var["valuesByMode"][mode_id]
        if isinstance(val, dict) and val.get("type") == "VARIABLE_ALIAS":
            return resolve(variables[val["id"]], mode_id)
        return "#%02x%02x%02x" % tuple(round(val[k] * 255) for k in "rgb")

    palettes = {}
    for var in variables.values():
        for mode_id in var["valuesByMode"]:
            palettes.setdefault(modes[mode_id], {})[var["name"]] = resolve(var, mode_id)
    return palettes


def oklab(hexstr):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(int(hexstr[i:i + 2], 16)) for i in (1, 3, 5))
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


class Theme:
    def __init__(self, palette, kind, defaults):
        self.p, self.kind, self.defaults = palette, kind, defaults
        self.cache, self.stack = {}, set()
        # snap targets: the neutral ramp plus the accents (bright/* and aliases are reserved)
        self.snap = {n: oklab(h) for n, h in palette.items() if n.startswith(("ramp/", "accent/"))}
        ramp = [f"ramp/{r}" for r in RAMP]
        self.by_light = sorted(ramp, key=lambda n: oklab(palette[n])[0])  # dark -> light

    # a colour value is (token, alpha) or None
    def spec(self, s):
        if isinstance(s, dict): s = s[self.kind]
        if s == NONE: return ("none", 0.0)
        tok, _, a = s.partition("@")
        if tok not in self.p: raise KeyError(f"unknown palette token {tok!r}")
        return (tok, float(a) / 100 if a else 1.0)

    def nearest(self, hexstr):
        h, a = hexstr[:7], int(hexstr[7:9] or "ff", 16) / 255
        if a == 0: return ("none", 0.0)
        target = oklab(h)
        return (min(self.snap, key=lambda n: math.dist(self.snap[n], target)), a)

    def step(self, val, direction):  # lighten/darken one shade along the ramp
        tok, a = val
        if tok not in self.by_light: return val
        i = self.by_light.index(tok) + direction
        return (self.by_light[max(0, min(i, len(self.by_light) - 1))], a)

    def evaluate(self, e):
        if e is None: return None
        if "hex" in e: return self.nearest(e["hex"])
        if "ref" in e: return self.color(e["ref"])
        if "unknown" in e: raise LookupError
        op = e["op"]
        if op == "transparent":
            v = self.evaluate(e["v"])
            return v and (v[0], v[1] * e["f"])
        if op in ("lighten", "darken"):
            v = self.evaluate(e["v"])
            return v and self.step(v, 1 if op == "lighten" else -1)
        if op in ("opaque", "mix"):
            v = self.evaluate(e["v"])
            return v and (v[0], 1.0)
        if op == "oneOf":
            return next((v for v in map(self.evaluate, e["vs"]) if v), None)
        if op == "ifDefined":
            return self.evaluate(e["then"] if self.evaluate(e["if"]) else e["else"])
        raise LookupError

    def color(self, key):
        if key in self.cache: return self.cache[key]
        if key in self.stack: return None  # cyclic default: treat as unset
        self.stack.add(key)
        try:
            if key in EXPLICIT:
                v = self.spec(EXPLICIT[key])
            else:
                try:
                    v = self.evaluate((self.defaults.get(key) or {}).get(self.kind))
                except LookupError:
                    v = self.spec(next(s for pat, s in FALLBACK if re.search(pat, key)))
        finally:
            self.stack.discard(key)
        self.cache[key] = v
        return v

    def hex(self, val):
        tok, a = val
        if tok == "none" or a <= 0: return "#00000000"
        h = self.p[tok]
        return h if a >= 1 else h + "%02x" % round(min(a, 1) * 255)


def build_mode(name, kind, palette, defaults):
    t = Theme(palette, kind, defaults)
    unknown = sorted(set(EXPLICIT) - set(defaults))
    colors = {}
    for key in sorted(set(defaults) | set(EXPLICIT)):
        v = t.color(key)
        if v is not None: colors[key] = t.hex(v)

    def fg(s):
        return t.hex(t.spec(s))
    token_colors = []
    for scopes, s, style in TOKENS:
        settings = {"foreground": fg(s)}
        if style: settings["fontStyle"] = style
        token_colors.append({"scope": scopes, "settings": settings})
    token_colors.insert(0, {"settings": {"foreground": fg("Text"), "background": fg("Surface")}})
    semantic = {k: (fg(v) if isinstance(v, str) else v) for k, v in SEMANTIC.items()}

    allowed = {h.lower() for h in palette.values()}  # every palette value, every mode alias
    for where, value in [*(("colors." + k, v) for k, v in colors.items()),
                         *(("tokenColors", r["settings"].get("foreground")) for r in token_colors),
                         *(("tokenColors", r["settings"].get("background")) for r in token_colors),
                         *(("semanticTokenColors." + k, v) for k, v in semantic.items() if isinstance(v, str))]:
        if value is None or value == "#00000000": continue
        assert value[:7].lower() in allowed, f"{name}: {where} = {value} is not a Greenpuccin colour"

    return {
        "$schema": "vscode://schemas/color-theme",
        "name": f"Greenpuccin {name}",
        "type": kind,
        "semanticHighlighting": True,
        "colors": colors,
        "tokenColors": token_colors,
        "semanticTokenColors": semantic,
    }, unknown


def main():
    palettes = load_palette(EXPORT)
    defaults = json.load(open(DEFAULTS, encoding="utf-8"))
    os.makedirs(os.path.join(OUT, "themes"), exist_ok=True)
    contributes = []
    for mode, kind in MODES.items():
        theme, unknown = build_mode(mode, kind, palettes[mode], defaults)
        fname = f"greenpuccin-{mode.lower()}-color-theme.json"
        with open(os.path.join(OUT, "themes", fname), "w", encoding="utf-8") as f:
            json.dump(theme, f, indent=2)
            f.write("\n")
        contributes.append({"label": theme["name"], "uiTheme": "vs-dark" if kind == "dark" else "vs",
                            "path": f"./themes/{fname}"})
        print(f"{theme['name']:20} {len(theme['colors'])} colours, {len(theme['tokenColors'])} token rules")
        if unknown: print("  note: set in EXPLICIT but not registered by this VSCodium:", ", ".join(unknown))
    pkg = {
        "name": "greenpuccin",
        "displayName": "Greenpuccin",
        "description": "Greenpuccin colour themes, generated from the Figcraft design-system export by theme/build.py.",
        "version": "1.0.0",
        "publisher": "local",
        "engines": {"vscode": "^1.80.0"},
        "categories": ["Themes"],
        "contributes": {"themes": contributes},
    }
    with open(os.path.join(OUT, "package.json"), "w", encoding="utf-8") as f:
        json.dump(pkg, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
