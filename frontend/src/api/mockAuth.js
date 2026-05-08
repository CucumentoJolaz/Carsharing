import axios from 'axios'

export async function initMockAuth(){
    const token = localStorage.getItem('access_token')
    if (token) {
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
        return
    }

    const response = await axios.get('/api/v1/users/mock-user/')
    const access = response.data.access


    localStorage.setItem('access-token', access)
    axios.defaults.headers.common['Authorization'] = `Bearer ${access}`
}