/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */

package org.tamuno.sqlgen.automate;

import java.sql.DatabaseMetaData;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Types;
import java.util.ArrayList;
import java.util.HashSet;

/**
 * @author kai
 * @TODO Documentation of class ColumnInfo
 */
public class ColumnInfo {
    
    public String name;
    public int type;
    public boolean isPrimaryKey;
    public boolean canBeNull;
    public boolean isAutoIncrement;
    public String size;
    public String defaultValue;
    
    
    public static ColumnInfo[] getColumnInfo(DatabaseMetaData meta, String catalog, String schema, String table) throws SQLException { 
        HashSet<String> primaryKeys = new HashSet<String>();
        ResultSet rs = meta.getPrimaryKeys(catalog, schema, table);
        while (rs.next()) {
            primaryKeys.add(rs.getString("COLUMN_NAME"));
        }
        rs.close();
        rs = meta.getColumns(catalog, schema, table, null);
        ArrayList<ColumnInfo> res = new ArrayList<ColumnInfo>();
        while (rs.next()) {
            ColumnInfo rinfo = new ColumnInfo();
            rinfo.type = rs.getInt("DATA_TYPE");
            rinfo.name = rs.getString("COLUMN_NAME");
            rinfo.isPrimaryKey = primaryKeys.contains(rinfo.name);
            rinfo.canBeNull = "YES".equals(rs.getString("IS_NULLABLE"));
            rinfo.size = rs.getString("COLUMN_SIZE");
            rinfo.defaultValue = rs.getString("COLUMN_DEF");
            try {
                rinfo.isAutoIncrement = "YES".equals(rs.getString("IS_AUTOINCREMENT"));
            } catch (SQLException sqle) {
                meta.getConnection().clearWarnings();
            }
            
            res.add(rinfo);
        }
        ColumnInfo result[] = new ColumnInfo[res.size()];
        return res.toArray(result);
    }
    
    public String getSQLGType() {
        switch (type) {
                case Types.INTEGER:
                    return "int";
                case Types.CLOB:
                    return "String";
                case Types.BOOLEAN:
                    return "boolean";
                case Types.FLOAT:
                    return "float";
                case Types.DOUBLE:
                    return "double";
                case Types.DECIMAL:
                    return "decimal";
                case Types.BIGINT:
                    return "long";
                case Types.VARCHAR:
                    return "String";
                case Types.BLOB:
                    return "bytes";
                case Types.TIMESTAMP:
                    return "Timestamp";
                case Types.TIME:
                    return "Time";
                case Types.REAL:
                    return "double";
                case Types.SMALLINT:
                    return "int";
                case Types.LONGVARBINARY:
                    return "bytes";
                default:
                    return "String";
           
        }
    }
    
}
