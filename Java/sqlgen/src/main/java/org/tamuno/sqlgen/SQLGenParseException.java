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

public class SQLGenParseException extends Exception {
    int pos;
    
    public SQLGenParseException(int pos, String message) {
        super(message);
        this.pos = pos;
    }
    
    public String toString() {
        return "Parse Exception on character "+pos + ": " + super.toString();
    }
    
}
