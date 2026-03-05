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
 * @TODO Documentation of class InsertRowCGen
 */
public class InsertRowCGen implements ITableCodeGenerator {
    
    
    public InsertRowCGen() {
        
    }

    
    
    public void appendCode(StringBuilder t, Connection connection, String catalog, String schema, String table) throws SQLException {
        ColumnInfo[] info = ColumnInfo.getColumnInfo(connection.getMetaData(), catalog, schema, table);
        t.append("insert");
        t.append(TamunoUtils.capitalize(table)+":=INSERT INTO "+table + "\n\t(\n");
        int c = 0;
        int mandatoryCount = 0;
        for (ColumnInfo column : info) {
            if (column.isAutoIncrement || column.canBeNull || (column.defaultValue!=null)) { 
                   continue;
            }
            if (c++>0) {
                    t.append(",\n");
            }
            t.append("\t\t" + column.name);
        }
        mandatoryCount = c;
        int oc=0;
        for (ColumnInfo column : info) {
            if (!(column.isAutoIncrement || column.canBeNull || (column.defaultValue!=null))) { 
                continue;
            }
            if (c++>0) {
                    if (mandatoryCount==0) {
                        t.append("\n\t\t[,][");
                    } else {
                        t.append("\n\t\t[,");
                    }      
            } else {
                t.append("\n\t\t[");
            }
            t.append("?"+column.name);
            String type = column.getSQLGType();
            if ("String".equals(type)) { 
                t.append(" " + column.name + "]");
                continue;
            }
            t.append(":"+type);
            t.append(" " + column.name + "]");
        }
        if (mandatoryCount==0) {
            t.append("\n\t\t[] /* prevents to combine both lists */\n");
        }
        t.append("\n\t)\n\tVALUES (\n");
        c = 0;
        for (ColumnInfo column : info) {
            if (column.isAutoIncrement || column.canBeNull || (column.defaultValue!=null)) { 
                continue;
            }
            if (c++>0) {
                    t.append(",\n");
            }
            t.append("\t\t$" + column.name);
        }
        oc=0;
        for (ColumnInfo column : info) {
            if (!(column.isAutoIncrement || column.canBeNull || (column.defaultValue!=null))) { 
                   continue;
            }
            if (c++>0) {
                    if (mandatoryCount==0) {
                        t.append("\n\t\t[,][,");
                    } else {
                        t.append("\n\t\t[,");
                    }      
            } else {
                t.append("\n\t\t[");
            }
            t.append(" $"+column.name);
            String type = column.getSQLGType();
            if ("String".equals(type)) { 
                t.append(" ]");
                continue;
            }
            t.append(":"+type);
            t.append(" ]");
        }
        t.append("\n\t);\n");
    }

}
