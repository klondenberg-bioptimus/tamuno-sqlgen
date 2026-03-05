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

class SQLGenToken {
    public SQLGenTokenType type;
    public String value;
    public String vartype = "String";
    public int pos;

    SQLGenToken(SQLGenTokenType type, String value) {
        this.type = type;
        this.value = value;
        
    }
    
    SQLGenToken(SQLGenTokenType type, String value, String vartype) {
        this.type = type;
        this.value = value;
        if (vartype!=null) {
            this.vartype = vartype;
        }
    }
    
}
