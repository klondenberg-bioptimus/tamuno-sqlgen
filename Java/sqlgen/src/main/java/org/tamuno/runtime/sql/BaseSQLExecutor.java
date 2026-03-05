/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */

package org.tamuno.runtime.sql;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;

/**
 * @author kai
 * @TODO Documentation of class BaseSQLExecutor
 */
public class BaseSQLExecutor {
        
        public int executeUpdate(Statement st, Object sql) throws SQLException {
            return st.executeUpdate(sql.toString());
        }
        
        public ResultSet executeQuery(Statement st, Object sql) throws SQLException {
            return st.executeQuery(sql.toString());
        }
}
