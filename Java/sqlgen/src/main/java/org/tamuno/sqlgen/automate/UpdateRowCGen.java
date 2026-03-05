/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */

package org.tamuno.sqlgen.automate;

import java.sql.Connection;
import java.sql.SQLException;
import org.tamuno.util.TamunoUtils;
/**
 * @author kai
 * @TODO Documentation of class UpdateRowCGen
 */
public class UpdateRowCGen implements ITableCodeGenerator {

    public void appendCode(StringBuilder t, Connection connection, String catalog, String schema, String table) throws SQLException {
        ColumnInfo[] info = ColumnInfo.getColumnInfo(connection.getMetaData(), catalog, schema, table);
        t.append("update");
        t.append(TamunoUtils.capitalize(table)+":=UPDATE "+table + "\n\tSET\n");
        int c = 0;
        for (ColumnInfo column : info) {
            if (column.isPrimaryKey) { 
                continue;
            }
            
            if (c++>0) {
                t.append("[,]\n");
            }
            t.append("\t\t[" + column.name + "=$"+column.name+"");
            String type = column.getSQLGType();
            if ("String".equals(type)) { 
                t.append("]");
                continue;
            }
            t.append(":"+type);
            t.append("]");
        }
        t.append("\n\tWHERE\n");
        c = 0;
        for (ColumnInfo column : info) {
            if (!column.isPrimaryKey) { 
                continue;
            }
            if (c++>0) {
                t.append(",\n");
            }
            t.append("\t\t" + column.name+ "=$"+column.name);
            String type = column.getSQLGType();
            if ("String".equals(type)) { 
                continue;
            }
            t.append(":"+type);
        }
        
        t.append("\n;\n");
    }

}
