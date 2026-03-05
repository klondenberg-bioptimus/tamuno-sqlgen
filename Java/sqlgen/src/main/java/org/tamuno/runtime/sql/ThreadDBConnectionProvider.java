/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */

package org.tamuno.runtime.sql;

import java.sql.Connection;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.logging.Level;
import javax.sql.DataSource;
import java.util.logging.Logger;

/**
 * @author kai
 * @TODO Documentation of class ThreadDBConnectionProvider
 */
public class ThreadDBConnectionProvider implements DBConnectionProvider {
    private DataSource dataSource;
    private Connection dbconn;
    private long lastCheck = 0;
    private long recheckInterval;
    
    public ThreadDBConnectionProvider(DataSource ds) {
        this(ds, 5000);
    }
    
    public ThreadDBConnectionProvider(DataSource ds, long recheckInterval) {
        this.dataSource = ds;
        this.recheckInterval = recheckInterval;
    }

    public Connection getConnection() throws SQLException {
        if (dbconn!=null) {
            if ((lastCheck+recheckInterval)>System.currentTimeMillis()) {
                return dbconn;
            } else {
                lastCheck = System.currentTimeMillis();
                return ensureConnection();
            }
        }
        dbconn = dataSource.getConnection();
        lastCheck = System.currentTimeMillis();
        return dbconn;
    }
    
    public void close() {
        if (dbconn!=null) {
            try {
                dbconn.close();
            } catch (SQLException t) {
                Logger.getLogger(this.getClass().getName()).log(Level.FINE, "Broken Database Connection", t);
            }
        }
    }
    
    public Statement getStatement() throws SQLException {
        return getConnection().createStatement();
    }
    
    /**
     * Ensures that a connection exists by getting a Statement, and running a simple query.
     * @throws java.sql.SQLException
     */
    public Connection ensureConnection() throws SQLException {
        try {
            Statement st = getStatement();
            st.execute("SELECT 1");
            st.close();
        } catch (SQLException sqle) {
            Logger.getLogger(this.getClass().getName()).log(Level.WARNING, "Broken Database Connection", sqle);
            dbconn = null;
        }
        return getConnection();
    }
    
    public Statement ensureStatement() throws SQLException {
        return ensureConnection().createStatement();
    }

    private void clearDBWarnings() {
        if (dbconn!=null) {
            try {
                dbconn.clearWarnings();
            } catch (SQLException sqle) {
                Logger.getLogger(this.getClass().getName()).log(Level.WARNING, "Broken Database Connection", sqle);
                dbconn = null;
            }
            
        }
    }
}
