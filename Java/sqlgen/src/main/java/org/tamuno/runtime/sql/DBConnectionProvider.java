/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */

package org.tamuno.runtime.sql;

import java.sql.Connection;
import java.sql.SQLException;

/**
 * @author kai
 * @TODO Documentation of class DBConnectionProvider
 */
public interface DBConnectionProvider {

        Connection getConnection() throws SQLException;
}
