/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */

package org.tamuno.sqlgen.automate;

import java.sql.Connection;
import java.sql.SQLException;

/**
 * @author kai
 * @TODO Documentation of class CrudsCGen
 */
public class CrudsCGen implements ITableCodeGenerator {

    private static InsertRowCGen create = new InsertRowCGen();
    private static UpdateRowCGen update = new UpdateRowCGen();
    private static DeleteRowCGen delete = new DeleteRowCGen();
    private static SelectRowCGen select = new SelectRowCGen();
    private static ListRowsCGen list = new ListRowsCGen();
    
    public void appendCode(StringBuilder append, Connection connection, String catalog, String schema, String table) throws SQLException {
        create.appendCode(append, connection, catalog, schema, table);
        append.append("\n");
        update.appendCode(append, connection, catalog, schema, table);
        append.append("\n");
        delete.appendCode(append, connection, catalog, schema, table);
        append.append("\n");
        select.appendCode(append, connection, catalog, schema, table);
        append.append("\n");
        list.appendCode(append, connection, catalog, schema, table);        
    }

}
