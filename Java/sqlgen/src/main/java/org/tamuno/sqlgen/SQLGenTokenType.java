/*

 Tamuno Framework 

Copyright: Kai Londenberg, 2007, Germany.

This software is made available as is, without any explicit
or implied warranties, to the extent permitted by law.

The Tamuno Framework is licensed under the Apache Public License V2.0
see LICENSE.txt

The TamunoFramework contains external Open Source Libraries, to
which the original Author has no copyright, and which are
available under their own licensing terms.

*/
package org.tamuno.sqlgen;

/**
 * Token Type to be used by SQLGenToken
 */
enum SQLGenTokenType {
    LITERAL,
    OPEN_BRACKET,
    CLOSE_BRACKET,
    REQUIRED_OPEN_BRACKET,
    REQUIRED_CLOSE_BRACKET,
    ESCAPED_VAR,
    LITERAL_VAR,
    TARGET_VAR,
    TYPE_SEPARATOR,
    OPTION_VAR
}
