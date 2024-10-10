# SPDX-FileCopyrightText: 2024 Carmen Bianca BAKKER <carmen@carmenbianca.eu>
# SPDX-FileCopyrightText: 2024 Free Software Foundation Europe e.V. <https://fsfe.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

""":mod:`gettext` plumbing of :mod:`reuse`."""

import gettext as _gettext_module
import os

_PACKAGE_PATH = os.path.dirname(__file__)
_LOCALE_DIR = os.path.join(_PACKAGE_PATH, "locale")

#: Translations object used throughout :mod:`reuse`. The translations
#: are sourced from ``reuse/locale/<lang>/LC_MESSAGES/reuse.mo``.
TRANSLATIONS: _gettext_module.NullTranslations = _gettext_module.translation(
    "reuse", localedir=_LOCALE_DIR, fallback=True
)
#: :meth:`gettext.NullTranslations.gettext` of :data:`TRANSLATIONS`
_ = TRANSLATIONS.gettext
#: :meth:`gettext.NullTranslations.gettext` of :data:`TRANSLATIONS`
gettext = TRANSLATIONS.gettext
#: :meth:`gettext.NullTranslations.ngettext` of :data:`TRANSLATIONS`
ngettext = TRANSLATIONS.ngettext
#: :meth:`gettext.NullTranslations.pgettext` of :data:`TRANSLATIONS`
pgettext = TRANSLATIONS.pgettext
#: :meth:`gettext.NullTranslations.npgettext` of :data:`TRANSLATIONS`
npgettext = TRANSLATIONS.npgettext
