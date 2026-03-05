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

package org.tamuno.runtime.sql;

/**
 * Basic interface for the results of generated SQL Select statements.
 * Allows to load a row from a result set into the object implementing this interface.
 */
public interface TypedRow extends Cloneable {

    /**
     * Allows to load a row from a result set into the object implementing this interface.
     * @param rs ResultSet to load the row data from.
     * @throws java.sql.SQLException
     */
    public void loadResultSetRow(java.sql.ResultSet rs) throws java.sql.SQLException;
    
    public Object clone();

}
